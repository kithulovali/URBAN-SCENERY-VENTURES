"""Signature verification and idempotent WhatsApp customer-assistant handling."""
from __future__ import annotations

import hashlib
import hmac
import logging
import os

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.platform_event_model import PlatformWebhookEvent
from services.platform_integrations import send_whatsapp_text

logger = logging.getLogger(__name__)


def verify_whatsapp_signature(raw_body: bytes, signature: str) -> None:
    app_secret = os.getenv("WHATSAPP_APP_SECRET", "").strip()
    if not app_secret:
        raise ValueError("WhatsApp webhook signature verification is not configured")
    if not signature.startswith("sha256="):
        raise ValueError("Missing or invalid webhook signature")
    expected = "sha256=" + hmac.new(
        app_secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("Invalid webhook signature")


def process_whatsapp_payload(payload: dict, db: Session) -> int:
    """Reply to unique inbound text messages without storing message text or sender numbers."""
    from services.ai_agents import run_agent

    processed = 0
    failures = 0
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue
                message_id = message.get("id")
                sender = message.get("from")
                text = message.get("text", {}).get("body", "").strip()
                if not message_id or not sender or not text:
                    continue

                logger.info("WhatsApp inbound text received (event_id=%s)", message_id)
                event = PlatformWebhookEvent(
                    event_id=str(message_id),
                    platform="whatsapp",
                    status="processing",
                )
                db.add(event)
                try:
                    db.commit()
                    event_id = event.id
                except IntegrityError:
                    db.rollback()
                    # Skip sent/in-progress duplicates, but permit retry after a prior failure.
                    existing = (
                        db.query(PlatformWebhookEvent)
                        .filter(PlatformWebhookEvent.event_id == str(message_id))
                        .first()
                    )
                    if existing is None or existing.status != "failed":
                        logger.info(
                            "WhatsApp duplicate skipped (event_id=%s, status=%s)",
                            message_id,
                            existing.status if existing else "unknown",
                        )
                        continue
                    existing.status = "processing"
                    db.commit()
                    event_id = existing.id

                try:
                    logger.info("WhatsApp customer-assistant started (event_id=%s)", message_id)
                    result = run_agent("customer_shopping_assistant", text, db)
                    answer = str(result.get("answer", "")).strip()
                    if not answer:
                        raise RuntimeError("Customer-shopping agent returned an empty answer")
                    logger.info(
                        "WhatsApp customer-assistant generated response (event_id=%s, model=%s)",
                        message_id,
                        result.get("model", "unknown"),
                    )
                    send_result = send_whatsapp_text(str(sender), answer[:4000])
                    provider_messages = send_result.get("messages") or []
                    provider_id = (
                        provider_messages[0].get("id")
                        if provider_messages and isinstance(provider_messages[0], dict)
                        else None
                    )
                    event = db.get(PlatformWebhookEvent, event_id)
                    if event is not None:
                        event.status = "sent"
                    db.commit()
                    processed += 1
                    logger.info(
                        "WhatsApp reply accepted by Meta (event_id=%s, provider_message_id=%s)",
                        message_id,
                        provider_id or "missing",
                    )
                except Exception:
                    failures += 1
                    db.rollback()
                    logger.exception(
                        "WhatsApp customer-assistant reply failed (event_id=%s)", message_id
                    )
                    try:
                        failed = db.get(PlatformWebhookEvent, event_id)
                        if failed is not None:
                            failed.status = "failed"
                            db.commit()
                    except Exception:
                        db.rollback()
                        logger.exception(
                            "Could not persist failed WhatsApp event status (event_id=%s)",
                            message_id,
                        )

    # Return a non-2xx webhook response if any reply failed. Meta can retry;
    # successful messages are idempotently skipped and failed events are retryable.
    if failures:
        raise RuntimeError(
            f"WhatsApp webhook processing failed for {failures} message(s); "
            f"{processed} message(s) were sent successfully."
        )
    return processed

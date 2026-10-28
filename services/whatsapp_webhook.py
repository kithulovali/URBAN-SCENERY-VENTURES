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

                event = PlatformWebhookEvent(
                    event_id=str(message_id),
                    platform="whatsapp",
                    status="processing",
                )
                db.add(event)
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    # Duplicate delivery: do not send a second customer reply.
                    continue

                event_id = event.id
                try:
                    answer = run_agent("customer_shopping_assistant", text, db)["answer"]
                    send_whatsapp_text(str(sender), answer[:4000])
                    event.status = "sent"
                    db.commit()
                    processed += 1
                except Exception:
                    db.rollback()
                    logger.exception("WhatsApp customer-assistant reply failed (event_id=%s)", message_id)
                    failed = db.get(PlatformWebhookEvent, event_id)
                    if failed is not None:
                        failed.status = "failed"
                        db.commit()
    return processed

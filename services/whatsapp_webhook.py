"""Verify Meta webhooks, maintain private conversation context, and reply idempotently."""
from __future__ import annotations

import hashlib
import hmac
import logging
import os

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.platform_event_model import PlatformWebhookEvent
from models.whatsapp_conversation_model import WhatsAppConversationMessage
from services.platform_integrations import send_whatsapp_text

logger = logging.getLogger(__name__)


def verify_whatsapp_signature(raw_body: bytes, signature: str) -> None:
    app_secret = os.getenv("WHATSAPP_APP_SECRET", "").strip()
    if not app_secret:
        raise ValueError("WhatsApp webhook signature verification is not configured")
    if not signature:
        raise ValueError("Missing or invalid webhook signature")
    prefix, separator, digest = signature.partition("=")
    if (prefix != "sha256" or separator != "="
            or len(digest) != hashlib.sha256().digest_size * 2
            or any(char not in "0123456789abcdefABCDEF" for char in digest)):
        raise ValueError("Missing or invalid webhook signature")
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, digest.lower()):
        raise ValueError("Invalid webhook signature")


def _conversation_key(sender: str) -> str:
    secret = (os.getenv("WHATSAPP_CONVERSATION_HASH_KEY")
              or os.getenv("WHATSAPP_APP_SECRET", "")).strip()
    if not secret:
        raise RuntimeError("WhatsApp conversation hashing is not configured")
    return hmac.new(secret.encode(), sender.encode(), hashlib.sha256).hexdigest()


def _message_text(message: dict) -> str:
    kind = message.get("type")
    if kind == "text":
        return str((message.get("text") or {}).get("body") or "").strip()
    if kind == "button":
        button = message.get("button") or {}
        return str(button.get("text") or button.get("payload") or "").strip()
    if kind == "interactive":
        interactive = message.get("interactive") or {}
        reply = interactive.get("button_reply") or interactive.get("list_reply") or {}
        return str(reply.get("title") or reply.get("description") or reply.get("id") or "").strip()
    return ""


def _history(db: Session, key: str, current_id: int) -> list[dict[str, str]]:
    rows = (db.query(WhatsAppConversationMessage)
            .filter(WhatsAppConversationMessage.conversation_key == key,
                    WhatsAppConversationMessage.id != current_id)
            .order_by(WhatsAppConversationMessage.id.desc()).limit(8).all())
    rows.reverse()
    return [{"role": "customer" if row.direction == "inbound" else "store",
             "content": row.message_text} for row in rows]


def _process_statuses(value: dict, db: Session) -> None:
    status_map = {"sent": "sent", "delivered": "delivered", "read": "read", "failed": "failed"}
    changed = False
    for item in value.get("statuses", []) or []:
        provider_id = item.get("id")
        provider_status = status_map.get(item.get("status"))
        if not provider_id or not provider_status:
            continue
        row = (db.query(WhatsAppConversationMessage)
               .filter(WhatsAppConversationMessage.message_id == str(provider_id)).first())
        if row is not None:
            row.delivery_status = provider_status
            changed = True
    if changed:
        db.commit()


def process_whatsapp_payload(payload: dict, db: Session) -> int:
    from services.ai_agents import run_agent

    processed = 0
    failures = 0
    entries = payload.get("entry", []) if isinstance(payload, dict) else []
    for entry in entries if isinstance(entries, list) else []:
        for change in entry.get("changes", []) or []:
            value = change.get("value") or {}
            if not isinstance(value, dict):
                continue
            _process_statuses(value, db)
            for message in value.get("messages", []) or []:
                if not isinstance(message, dict):
                    continue
                message_id = str(message.get("id") or "")
                sender = str(message.get("from") or "")
                incoming_text = _message_text(message)
                if not message_id or not sender or not incoming_text:
                    continue
                key = _conversation_key(sender)
                try:
                    event = PlatformWebhookEvent(event_id=message_id,
                                                 platform="whatsapp", status="processing")
                    db.add(event)
                    db.commit()
                    event_id = event.id
                except IntegrityError:
                    db.rollback()
                    existing = (db.query(PlatformWebhookEvent)
                                .filter(PlatformWebhookEvent.event_id == message_id).first())
                    if existing is None or existing.status != "failed":
                        logger.info("WhatsApp duplicate skipped (event_id=%s)", message_id)
                        continue
                    existing.status = "processing"
                    db.commit()
                    event_id = existing.id

                try:
                    inbound = (db.query(WhatsAppConversationMessage)
                               .filter(WhatsAppConversationMessage.message_id == message_id).first())
                    if inbound is None:
                        inbound = WhatsAppConversationMessage(
                            conversation_key=key, message_id=message_id, direction="inbound",
                            message_text=incoming_text, delivery_status="received")
                        db.add(inbound)
                        db.commit()
                    history = _history(db, key, inbound.id)
                    result = run_agent("customer_shopping_assistant", incoming_text, db,
                                       conversation_history=history)
                    answer = str(result.get("answer") or "").strip()
                    if not answer:
                        raise RuntimeError("Customer-shopping assistant returned an empty answer")
                    sent = send_whatsapp_text(sender, answer[:4000])
                    provider_messages = sent.get("messages") or []
                    provider_id = (provider_messages[0].get("id")
                                   if provider_messages and isinstance(provider_messages[0], dict)
                                   else None)
                    if not provider_id:
                        raise RuntimeError("WhatsApp provider did not return an outbound message ID")
                    db.add(WhatsAppConversationMessage(
                        conversation_key=key, message_id=str(provider_id), direction="outbound",
                        message_text=answer[:4000], delivery_status="accepted"))
                    event = db.get(PlatformWebhookEvent, event_id)
                    if event is not None:
                        event.status = "sent"
                    db.commit()
                    processed += 1
                    logger.info("WhatsApp reply accepted (event_id=%s, provider_message_id=%s)",
                                message_id, provider_id)
                except Exception:
                    failures += 1
                    db.rollback()
                    logger.exception("WhatsApp customer-assistant processing failed (event_id=%s)",
                                     message_id)
                    try:
                        failed = db.get(PlatformWebhookEvent, event_id)
                        if failed is not None:
                            failed.status = "failed"
                            db.commit()
                    except Exception:
                        db.rollback()
                        logger.exception("Could not persist failed WhatsApp event (event_id=%s)",
                                         message_id)
    if failures:
        raise RuntimeError(f"WhatsApp webhook processing failed for {failures} message(s); "
                           f"{processed} message(s) were accepted by the provider.")
    return processed

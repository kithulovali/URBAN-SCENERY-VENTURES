import hashlib
import hmac

import pytest

from services.whatsapp_webhook import process_whatsapp_payload, verify_whatsapp_signature


def test_whatsapp_webhook_signature_is_verified(monkeypatch):
    secret = "test-app-secret"
    body = b'{"object":"whatsapp_business_account"}'
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)

    verify_whatsapp_signature(body, signature)

    with pytest.raises(ValueError, match="Invalid webhook signature"):
        verify_whatsapp_signature(body, "sha256=" + "0" * 64)


def test_whatsapp_customer_assistant_deduplicates_provider_retries(session, monkeypatch):
    import services.ai_agents as ai_agents
    import services.whatsapp_webhook as webhook

    replies = []
    monkeypatch.setattr(
        ai_agents,
        "run_agent",
        lambda agent, question, db: {
            "agent": agent,
            "answer": "I can help you find an in-stock product.",
            "model": "test-model",
            "data_summary": {},
        },
    )
    monkeypatch.setattr(
        webhook,
        "send_whatsapp_text",
        lambda recipient, message: replies.append((recipient, message)) or {"messages": [{"id": "out-1"}]},
    )
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "id": "wamid.test-message-1",
                        "from": "256700000000",
                        "type": "text",
                        "text": {"body": "Do you have a laptop?"},
                    }]
                }
            }]
        }]
    }

    assert process_whatsapp_payload(payload, session) == 1
    assert process_whatsapp_payload(payload, session) == 0
    assert replies == [("256700000000", "I can help you find an in-stock product.")]

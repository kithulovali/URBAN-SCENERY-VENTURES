import hashlib
import hmac

import pytest

from services.whatsapp_webhook import process_whatsapp_payload, verify_whatsapp_signature


def _signature(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_whatsapp_webhook_signature_is_verified(monkeypatch):
    secret = "synthetic-test-app-secret"
    # Whitespace is intentional: the HMAC must use the exact raw bytes, not parsed JSON.
    body = b'{ "object" : "whatsapp_business_account" }'
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)

    verify_whatsapp_signature(body, _signature(secret, body))

    with pytest.raises(ValueError, match="Invalid webhook signature"):
        verify_whatsapp_signature(body, _signature(secret, body + b" "))


@pytest.mark.parametrize("signature", [
    "",
    "sha1=" + "a" * 64,
    "sha256=",
    "sha256=" + "g" * 64,
    "sha256=" + "a" * 63,
    "sha256=" + "a" * 65,
])
def test_whatsapp_webhook_rejects_missing_or_malformed_signature(monkeypatch, signature):
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "synthetic-test-app-secret")
    with pytest.raises(ValueError, match="Missing or invalid webhook signature"):
        verify_whatsapp_signature(b'{"object":"whatsapp_business_account"}', signature)


def test_whatsapp_webhook_requires_app_secret(monkeypatch):
    monkeypatch.delenv("WHATSAPP_APP_SECRET", raising=False)
    with pytest.raises(ValueError, match="not configured"):
        verify_whatsapp_signature(b"{}", "sha256=" + "a" * 64)


def test_whatsapp_customer_assistant_deduplicates_provider_retries(session, monkeypatch):
    import services.ai_agents as ai_agents
    import services.whatsapp_webhook as webhook

    monkeypatch.setenv("WHATSAPP_APP_SECRET", "synthetic-conversation-key")
    replies = []
    monkeypatch.setattr(
        ai_agents,
        "run_agent",
        lambda agent, question, db, conversation_history=None: {
            "agent": agent,
            "answer": "I can help you find an in-stock product.",
            "model": "test-model",
            "data_summary": {},
        },
    )
    monkeypatch.setattr(
        webhook,
        "send_whatsapp_text",
        lambda recipient, message: replies.append((recipient, message))
        or {"messages": [{"id": "out-1"}]},
    )
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "field": "messages",
                "value": {
                    "messages": [{
                        "id": "wamid.synthetic-message-1",
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


@pytest.mark.parametrize("payload", [
    {"object": "whatsapp_business_account", "entry": []},
    {"object": "whatsapp_business_account", "entry": [{
        "changes": [{"value": {"statuses": [{"id": "wamid.synthetic"}]}}]
    }]},
])
def test_non_message_notifications_are_ignored(session, monkeypatch, payload):
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "synthetic-conversation-key")
    import services.ai_agents as ai_agents
    import services.whatsapp_webhook as webhook

    monkeypatch.setattr(
        ai_agents, "run_agent",
        lambda *args, **kwargs: pytest.fail("Agent must not run for non-message notifications"),
    )
    monkeypatch.setattr(
        webhook, "send_whatsapp_text",
        lambda *args, **kwargs: pytest.fail("No reply should be sent for non-message notifications"),
    )
    assert process_whatsapp_payload(payload, session) == 0


def test_failed_agent_is_not_acknowledged_as_success(session, monkeypatch):
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "synthetic-conversation-key")
    import services.ai_agents as ai_agents
    import services.whatsapp_webhook as webhook
    from models.platform_event_model import PlatformWebhookEvent

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": "wamid.synthetic-failure",
            "from": "256700000000",
            "type": "text",
            "text": {"body": "Find a laptop"},
        }]}}]}]
    }
    monkeypatch.setattr(
        ai_agents, "run_agent",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("synthetic agent failure")),
    )
    monkeypatch.setattr(
        webhook, "send_whatsapp_text",
        lambda *args, **kwargs: pytest.fail("Must not send when the agent fails"),
    )

    with pytest.raises(RuntimeError, match="processing failed"):
        process_whatsapp_payload(payload, session)

    event = session.query(PlatformWebhookEvent).filter_by(
        event_id="wamid.synthetic-failure"
    ).one()
    assert event.status == "failed"


def test_conversation_history_is_reused_and_phone_number_is_not_stored(session, monkeypatch):
    import services.ai_agents as ai_agents
    import services.whatsapp_webhook as webhook
    from models.whatsapp_conversation_model import WhatsAppConversationMessage

    monkeypatch.setenv("WHATSAPP_APP_SECRET", "synthetic-conversation-key")
    captured = []
    monkeypatch.setattr(
        ai_agents, "run_agent",
        lambda agent, question, db, conversation_history=None: (
            captured.append((question, conversation_history or []))
            or {"answer": "I can help with that.", "model": "test-model"}
        ),
    )
    monkeypatch.setattr(
        webhook, "send_whatsapp_text",
        lambda recipient, message: {"messages": [{"id": "out-" + str(len(captured))}]},
    )

    def payload(message_id, body):
        return {"entry": [{"changes": [{"value": {"messages": [{
            "id": message_id, "from": "256700000000",
            "type": "text", "text": {"body": body},
        }]}}]}]}

    assert process_whatsapp_payload(payload("in-1", "I need a laptop"), session) == 1
    assert process_whatsapp_payload(payload("in-2", "My budget is 1 million"), session) == 1

    assert captured[1][0] == "My budget is 1 million"
    assert captured[1][1] == [
        {"role": "customer", "content": "I need a laptop"},
        {"role": "store", "content": "I can help with that."},
    ]
    rows = session.query(WhatsAppConversationMessage).order_by(
        WhatsAppConversationMessage.id
    ).all()
    assert len(rows) == 4
    assert all("256700000000" not in row.conversation_key for row in rows)
    assert all(row.conversation_key == rows[0].conversation_key for row in rows)


def test_unsupported_media_receives_a_text_fallback_instead_of_being_silently_ignored(session, monkeypatch):
    import services.ai_agents as ai_agents
    import services.whatsapp_webhook as webhook

    monkeypatch.setenv("WHATSAPP_APP_SECRET", "synthetic-conversation-key")
    captured = []
    monkeypatch.setattr(
        ai_agents, "run_agent",
        lambda agent, question, db, conversation_history=None: (
            captured.append(question)
            or {"answer": "Please describe the item in a text message.", "model": "test-model"}
        ),
    )
    monkeypatch.setattr(
        webhook, "send_whatsapp_text",
        lambda recipient, message: {"messages": [{"id": "out-media-1"}]},
    )
    payload = {"entry": [{"changes": [{"value": {"messages": [{
        "id": "wamid.media-1", "from": "256700000000", "type": "image",
        "image": {"id": "media-id"},
    }]}}]}]}

    assert process_whatsapp_payload(payload, session) == 1
    assert len(captured) == 1
    assert "sent an image" in captured[0].lower()


def test_delivery_status_received_before_outbound_row_is_applied_later(session, monkeypatch):
    import services.ai_agents as ai_agents
    import services.whatsapp_webhook as webhook
    from models.whatsapp_conversation_model import WhatsAppConversationMessage

    monkeypatch.setenv("WHATSAPP_APP_SECRET", "synthetic-conversation-key")
    monkeypatch.setattr(
        ai_agents, "run_agent",
        lambda *args, **kwargs: {"answer": "Here are the details.", "model": "test-model"},
    )
    monkeypatch.setattr(
        webhook, "send_whatsapp_text",
        lambda *args, **kwargs: {"messages": [{"id": "wamid.outbound-early-status"}]},
    )
    status_payload = {"entry": [{"changes": [{"value": {"statuses": [{
        "id": "wamid.outbound-early-status", "status": "read",
    }]}}]}]}
    assert process_whatsapp_payload(status_payload, session) == 0

    message_payload = {"entry": [{"changes": [{"value": {"messages": [{
        "id": "wamid.inbound-after-status", "from": "256700000000",
        "type": "text", "text": {"body": "Tell me about this product"},
    }]}}]}]}
    assert process_whatsapp_payload(message_payload, session) == 1
    outbound = session.query(WhatsAppConversationMessage).filter_by(
        message_id="wamid.outbound-early-status"
    ).one()
    assert outbound.delivery_status == "read"

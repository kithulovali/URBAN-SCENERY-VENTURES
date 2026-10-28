"""Admin-controlled endpoints for outbound platform actions."""
import hmac
import json
import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, HttpUrl
from starlette.concurrency import run_in_threadpool

from settings import sessionlocal
from services.whatsapp_webhook import verify_whatsapp_signature, process_whatsapp_payload

from core.security import get_current_admin
from services.platform_integrations import (
    platform_status,
    send_whatsapp_text,
    publish_facebook_post,
    publish_instagram_image,
    publish_tiktok_video,
)

router = APIRouter(prefix="/platforms", tags=["Platform Integrations"])


class ApprovedAction(BaseModel):
    approved: bool = Field(..., description="Explicit administrator confirmation for this outbound action")


class WhatsAppMessage(ApprovedAction):
    to: str = Field(..., min_length=8, max_length=20, description="Recipient phone number in international format")
    message: str = Field(..., min_length=1, max_length=4096)


class FacebookPost(ApprovedAction):
    message: str = Field(..., min_length=1, max_length=5000)


class InstagramImagePost(ApprovedAction):
    image_url: HttpUrl
    caption: str = Field("", max_length=2200)


class TikTokVideoPost(ApprovedAction):
    video_url: HttpUrl
    caption: str = Field("", max_length=2200)
    privacy_level: str = Field(..., pattern="^(PUBLIC_TO_EVERYONE|MUTUAL_FOLLOW_FRIENDS|FOLLOWER_OF_CREATOR|SELF_ONLY)$")



class MultiPlatformCampaign(ApprovedAction):
    platforms: list[Literal["facebook", "instagram", "tiktok"]] = Field(..., min_length=1)
    caption: str = Field(..., min_length=1, max_length=2200)
    image_url: HttpUrl | None = None
    video_url: HttpUrl | None = None
    privacy_level: str | None = Field(
        None,
        pattern="^(PUBLIC_TO_EVERYONE|MUTUAL_FOLLOW_FRIENDS|FOLLOWER_OF_CREATOR|SELF_ONLY)$",
    )


def _require_approval(approved: bool) -> None:
    if not approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Outbound action requires explicit administrator approval.",
        )


@router.get("/status", dependencies=[Depends(get_current_admin)])
def get_platform_status():
    """Return whether required settings exist; credentials are never returned."""
    return platform_status()


@router.post("/whatsapp/messages", dependencies=[Depends(get_current_admin)])
def whatsapp_message(payload: WhatsAppMessage):
    _require_approval(payload.approved)
    try:
        result = send_whatsapp_text(payload.to, payload.message)
        messages = result.get("messages") or []
        provider_id = messages[0].get("id") if messages and isinstance(messages[0], dict) else None
        return {"platform": "whatsapp", "status": "accepted_by_provider", "provider_id": provider_id}
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/facebook/publish", dependencies=[Depends(get_current_admin)])
def facebook_publish(payload: FacebookPost):
    _require_approval(payload.approved)
    try:
        result = publish_facebook_post(payload.message)
        return {"platform": "facebook", "status": "published", "provider_id": result.get("id")}
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/instagram/publish-image", dependencies=[Depends(get_current_admin)])
def instagram_publish(payload: InstagramImagePost):
    _require_approval(payload.approved)
    try:
        result = publish_instagram_image(str(payload.image_url), payload.caption)
        return {"platform": "instagram", "status": "published", "provider_id": result.get("id")}
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/tiktok/publish-video", dependencies=[Depends(get_current_admin)])
def tiktok_publish(payload: TikTokVideoPost):
    _require_approval(payload.approved)
    try:
        result = publish_tiktok_video(str(payload.video_url), payload.caption, payload.privacy_level)
        return {"platform": "tiktok", **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc



@router.post("/campaign/publish", dependencies=[Depends(get_current_admin)])
def publish_campaign(payload: MultiPlatformCampaign):
    """Publish one approved campaign to selected social channels and report per-channel outcomes."""
    _require_approval(payload.approved)
    outcomes = {}
    for platform in dict.fromkeys(payload.platforms):
        try:
            if platform == "facebook":
                result = publish_facebook_post(payload.caption)
                outcomes[platform] = {"status": "published", "provider_id": result.get("id")}
            elif platform == "instagram":
                if not payload.image_url:
                    outcomes[platform] = {"status": "skipped", "reason": "image_url is required"}
                    continue
                result = publish_instagram_image(str(payload.image_url), payload.caption)
                outcomes[platform] = {"status": "published", "provider_id": result.get("id")}
            elif platform == "tiktok":
                if not payload.video_url or not payload.privacy_level:
                    outcomes[platform] = {
                        "status": "skipped",
                        "reason": "video_url and privacy_level are required",
                    }
                    continue
                result = publish_tiktok_video(
                    str(payload.video_url), payload.caption, payload.privacy_level
                )
                outcomes[platform] = result
        except ValueError as exc:
            outcomes[platform] = {"status": "failed", "reason": str(exc)}
        except RuntimeError as exc:
            outcomes[platform] = {"status": "failed", "reason": str(exc)}
    statuses = [item.get("status") for item in outcomes.values()]
    if statuses and all(value == "published" for value in statuses):
        overall = "completed"
    elif statuses and all(value in {"published", "submitted_for_processing"} for value in statuses):
        overall = "submitted_for_processing"
    elif any(value in {"published", "submitted_for_processing"} for value in statuses):
        overall = "partial_failure"
    else:
        overall = "failed"
    return {"status": overall, "approved": True, "outcomes": outcomes}



@router.get("/webhooks/whatsapp", response_class=PlainTextResponse)
def verify_whatsapp_webhook(
    mode: str | None = Query(None, alias="hub.mode"),
    token: str | None = Query(None, alias="hub.verify_token"),
    challenge: str | None = Query(None, alias="hub.challenge"),
):
    """Meta webhook subscription verification endpoint."""
    expected = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "").strip()
    if mode == "subscribe" and expected and token and hmac.compare_digest(token, expected) and challenge:
        return challenge
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Webhook verification failed")


@router.post("/webhooks/whatsapp")
async def receive_whatsapp_webhook(request: Request):
    """Verify Meta's signature and pass unique inbound text messages to the shopping assistant."""
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    try:
        verify_whatsapp_signature(raw_body, signature)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON webhook payload") from exc
    def process_with_own_session() -> int:
        with sessionlocal() as db:
            return process_whatsapp_payload(payload, db)

    processed = await run_in_threadpool(process_with_own_session)
    return {"status": "accepted", "processed_messages": processed}

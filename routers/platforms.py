"""Admin-controlled endpoints for outbound platform actions."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.orm import Session

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
        return {"platform": "whatsapp", "status": "accepted_by_provider", "provider_id": result.get("messages", [{}])[0].get("id")}
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

"""Credential-safe status and controlled publishing adapters for external platforms."""
from __future__ import annotations

import os
from typing import Any

import httpx


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def platform_status() -> dict[str, dict[str, Any]]:
    """Report configuration presence only; this does not prove a token is valid."""
    graph_version = _env("META_GRAPH_API_VERSION")
    meta_token = _env("META_GRAPH_ACCESS_TOKEN")
    return {
        "whatsapp": {
            "configured": bool(_env("WHATSAPP_ACCESS_TOKEN") and _env("WHATSAPP_PHONE_NUMBER_ID") and graph_version),
            "required_env": ["WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "META_GRAPH_API_VERSION"],
            "webhook_configured": bool(_env("WHATSAPP_APP_SECRET") and _env("WHATSAPP_WEBHOOK_VERIFY_TOKEN")),
        },
        "facebook": {
            "configured": bool(_env("FACEBOOK_PAGE_ID") and _env("FACEBOOK_PAGE_ACCESS_TOKEN") and graph_version),
            "required_env": ["FACEBOOK_PAGE_ID", "FACEBOOK_PAGE_ACCESS_TOKEN", "META_GRAPH_API_VERSION"],
        },
        "instagram": {
            "configured": bool(_env("INSTAGRAM_BUSINESS_ACCOUNT_ID") and meta_token and graph_version),
            "required_env": ["INSTAGRAM_BUSINESS_ACCOUNT_ID", "META_GRAPH_ACCESS_TOKEN", "META_GRAPH_API_VERSION"],
        },
        "tiktok": {
            "configured": bool(_env("TIKTOK_ACCESS_TOKEN") and _env("TIKTOK_OPEN_ID")),
            "required_env": ["TIKTOK_ACCESS_TOKEN", "TIKTOK_OPEN_ID"],
        },
        "image_generation": {
            "configured": bool(_env("GOOGLE_API_KEY") or _env("GEMINI_API_KEY")),
            "required_env": ["GOOGLE_API_KEY or GEMINI_API_KEY"],
            "note": "A key enables provider access but does not confirm image-model availability or billing.",
        },
    }


def _meta_url(resource: str) -> str:
    version = _env("META_GRAPH_API_VERSION")
    if not version:
        raise ValueError("META_GRAPH_API_VERSION is not configured")
    return f"https://graph.facebook.com/{version}/{resource.lstrip('/')}"


def _post_meta(resource: str, data: dict[str, Any], token: str) -> dict[str, Any]:
    if not token:
        raise ValueError("Required Meta access token is not configured")
    payload = {**data, "access_token": token}
    try:
        response = httpx.post(_meta_url(resource), data=payload, timeout=20.0)
        response.raise_for_status()
        result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError("Meta platform request failed; verify credentials, permissions, and payload.") from exc
    if not isinstance(result, dict) or result.get("error"):
        raise RuntimeError("Meta platform rejected the request; verify credentials, permissions, and payload.")
    return result


def send_whatsapp_text(to: str, message: str) -> dict[str, Any]:
    token = _env("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = _env("WHATSAPP_PHONE_NUMBER_ID")
    if not token or not phone_number_id:
        raise ValueError("WhatsApp Cloud API credentials are not configured")
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": message},
    }
    return _post_meta(f"{phone_number_id}/messages", body, token)


def publish_facebook_post(message: str) -> dict[str, Any]:
    page_id = _env("FACEBOOK_PAGE_ID")
    token = _env("FACEBOOK_PAGE_ACCESS_TOKEN")
    if not page_id or not token:
        raise ValueError("Facebook Page credentials are not configured")
    return _post_meta(f"{page_id}/feed", {"message": message}, token)


def publish_instagram_image(image_url: str, caption: str) -> dict[str, Any]:
    account_id = _env("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    token = _env("META_GRAPH_ACCESS_TOKEN")
    if not account_id or not token:
        raise ValueError("Instagram Business credentials are not configured")
    # Instagram requires a publicly accessible image URL and a two-step publish flow.
    container = _post_meta(
        f"{account_id}/media",
        {"image_url": image_url, "caption": caption},
        token,
    )
    creation_id = container.get("id")
    if not creation_id:
        raise RuntimeError("Instagram did not return a media container ID")
    return _post_meta(
        f"{account_id}/media_publish",
        {"creation_id": creation_id},
        token,
    )


def publish_tiktok_video(video_url: str, caption: str, privacy_level: str) -> dict[str, Any]:
    token = _env("TIKTOK_ACCESS_TOKEN")
    if not token or not _env("TIKTOK_OPEN_ID"):
        raise ValueError("TikTok Content Posting API credentials are not configured")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        creator_response = httpx.post(
            "https://open.tiktokapis.com/v2/post/publish/creator_info/query/",
            headers=headers,
            json={},
            timeout=20.0,
        )
        creator_response.raise_for_status()
        creator_result = creator_response.json()
        allowed = creator_result.get("data", {}).get("privacy_level_options", [])
        if privacy_level not in allowed:
            raise ValueError("privacy_level is not among the creator's current allowed options")
        response = httpx.post(
            "https://open.tiktokapis.com/v2/post/publish/video/init/",
            headers=headers,
            json={
                "post_info": {
                    "title": caption,
                    "privacy_level": privacy_level,
                    "brand_content_toggle": False,
                    "brand_organic_toggle": True,
                },
                "source_info": {"source": "PULL_FROM_URL", "video_url": video_url},
            },
            timeout=20.0,
        )
        response.raise_for_status()
        result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith("privacy_level"):
            raise
        raise RuntimeError("TikTok request failed; verify token, scopes, verified media domain, and payload.") from exc
    error = result.get("error", {})
    if error and error.get("code") not in (None, "ok"):
        raise RuntimeError("TikTok rejected the request; verify token, scopes, verified media domain, and payload.")
    data = result.get("data", {})
    if not data.get("publish_id"):
        raise RuntimeError("TikTok did not return a publish ID")
    # TikTok processing is asynchronous; this is an accepted request, not proof of publication.
    return {"publish_id": data["publish_id"], "status": "submitted_for_processing"}

from services.platform_integrations import platform_status


def test_platform_status_reports_missing_credentials_without_exposing_secrets(monkeypatch):
    names = [
        "META_GRAPH_API_VERSION",
        "META_GRAPH_ACCESS_TOKEN",
        "FACEBOOK_PAGE_ID",
        "FACEBOOK_PAGE_ACCESS_TOKEN",
        "INSTAGRAM_BUSINESS_ACCOUNT_ID",
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
        "TIKTOK_ACCESS_TOKEN",
        "TIKTOK_OPEN_ID",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
    ]
    for name in names:
        monkeypatch.delenv(name, raising=False)

    status = platform_status()

    assert set(status) == {"whatsapp", "facebook", "instagram", "tiktok", "image_generation"}
    assert all(item["configured"] is False for item in status.values())
    assert all("token" not in str(item).lower() for item in status.values())

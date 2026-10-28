"""Minimal idempotency record for inbound external webhook events."""
from datetime import datetime
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from settings import Model


class PlatformWebhookEvent(Model):
    __tablename__ = "platform_webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="processing")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

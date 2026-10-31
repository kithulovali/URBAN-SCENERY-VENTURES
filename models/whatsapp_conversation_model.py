"""Privacy-conscious WhatsApp conversation records."""
from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from settings import Model


class WhatsAppConversationMessage(Model):
    __tablename__ = "whatsapp_conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(32), nullable=False, default="received")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

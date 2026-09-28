from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TelegramMessageState(Base):
    __tablename__ = "telegram_message_states"

    id: Mapped[int] = mapped_column(primary_key=True)

    django_message_id: Mapped[int] = mapped_column(unique=True)

    token: Mapped[str] = mapped_column(String(255))

    chat_id: Mapped[str] = mapped_column(String(100), index=True)

    telegram_message_id: Mapped[int | None] = mapped_column(nullable=True)

    reply_markup: Mapped[list | None] = mapped_column(JSON, nullable=True)

    action: Mapped[str] = mapped_column(String(20))
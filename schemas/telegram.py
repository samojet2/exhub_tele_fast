from pydantic import BaseModel
from typing import Literal

class TelegramMessage(BaseModel):
    id: int
    token: str
    chat_id: int
    message_id: str
    text: str
    reply_markup: list | None = None
    action: Literal["new", "edit", "recreate"]

class TelegramBatch(BaseModel):
    batch_id: str
    messages: list[TelegramMessage]
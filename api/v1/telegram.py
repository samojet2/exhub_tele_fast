import json
from workers.batch_manager import (
    create_batch,
    wait_for_batch,
    collect_batch_result
)
import asyncio
from fastapi import APIRouter, UploadFile, File, Form
from services.telegram.service import TelegramService
from schemas.telegram import TelegramMessage, TelegramBatch
from workers.queue import message_queue

router = APIRouter(
    prefix="/telegram",
    tags=["Telegram"],
)

telegram_service = TelegramService()

@router.post("/send-message")
async def send_message(
    telegram_message: TelegramMessage,
):
    print("CHAT ID:", telegram_message.chat_id)
    print("TEXT:", telegram_message.text)
    print("TOKEN:", telegram_message.token)
    print("REPLY MARKUP:", telegram_message.reply_markup)

    await telegram_service.send_message(
        token=telegram_message.token,
        chat_id=telegram_message.chat_id,
        text=telegram_message.text,
        reply_markup=telegram_message.reply_markup,
    )

    return {
        "status": "sent",
    }

@router.post("/send-document")
async def send_document(
    chat_id: int = Form(...),
    text: str = Form(...),
    file: UploadFile = File(...),
    token: str | None = Form(None),
    reply_markup: str | None = Form(None),
):
    reply_markup_data = (
        json.loads(reply_markup)
        if reply_markup
        else None
    )

    print("CHAT ID:", chat_id)
    print("TEXT:", text)
    print("TOKEN:", token)
    print("FILE:", file.filename)
    print("REPLY MARKUP:", reply_markup_data)

    return {
        "status": "ok",
        "message": "document endpoint works",
    }



@router.post("/send-batch")
async def send_batch(
    data: TelegramBatch,
):

    create_batch(
        batch_id=data.batch_id,
        total=len(data.messages),
    )

    for message in data.messages:

        await message_queue.put({
            "batch_id": data.batch_id,
            "message": message.model_dump(),
        })

    asyncio.create_task(
        collect_batch_result(
            data.batch_id
        )
    )

    return {
        "status": "accepted",
        "batch_id": data.batch_id,
        "count": len(data.messages),
    }
from services.telegram.sender import TelegramSender


class TelegramService:

    def __init__(self):
        self.sender = TelegramSender()


    async def send_message(
        self,
        token: str,
        chat_id: int,
        text: str,
        reply_markup=None,
    ):
        return await self.sender.send_message(
            token=token,
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
        )


    async def edit_message(
        self,
        token: str,
        chat_id: int,
        message_id: str,
        text: str,
        reply_markup=None,
    ):
        return await self.sender.edit_message(
            token=token,
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
        )


    async def delete_message(
        self,
        token: str,
        chat_id: int,
        message_id: str,
    ):
        return await self.sender.delete_message(
            token=token,
            chat_id=chat_id,
            message_id=message_id,
        )
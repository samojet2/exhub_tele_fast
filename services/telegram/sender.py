from telegram import Bot

from services.telegram.markup import build_reply_markup


class TelegramSender:

    async def send_message(
        self,
        token: str,
        chat_id: int,
        text: str,
        reply_markup=None,
    ):

        bot = Bot(token=token)

        try:
            return await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=build_reply_markup(
                    reply_markup
                ),
            )

        finally:
            await bot.shutdown()


    async def edit_message(
        self,
        token: str,
        chat_id: int,
        message_id: str,
        text: str,
        reply_markup=None,
    ):

        bot = Bot(token=token)

        try:
            return await bot.edit_message_text(
                chat_id=chat_id,
                message_id=int(message_id),
                text=text,
                reply_markup=build_reply_markup(
                    reply_markup
                ),
            )

        finally:
            await bot.shutdown()


    async def delete_message(
        self,
        token: str,
        chat_id: int,
        message_id: str,
    ):

        bot = Bot(token=token)

        try:
            return await bot.delete_message(
                chat_id=chat_id,
                message_id=int(message_id),
            )

        finally:
            await bot.shutdown()
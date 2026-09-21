from services.telegram.service import TelegramService
from workers.batch_manager import add_result
from workers.queue import message_queue


telegram_service = TelegramService()


async def message_worker(worker_id: int):

    while True:

        job = await message_queue.get()

        batch_id = job["batch_id"]
        message = job["message"]

        try:

            # --------------------------------
            # NEW
            # --------------------------------

            if message["action"] == "new":

                telegram_message = (
                    await telegram_service.send_message(
                        token=message["token"],
                        chat_id=message["chat_id"],
                        text=message["text"],
                        reply_markup=message["reply_markup"],
                    )
                )

                result = {
                    "id": message["id"],
                    "chat_id": message["chat_id"],
                    "message_id": str(
                        telegram_message.message_id
                    ),
                    "status": "sent",
                    "worker": worker_id,
                }

            # --------------------------------
            # EDIT
            # --------------------------------

            elif message["action"] == "edit":

                telegram_message = (
                    await telegram_service.edit_message(
                        token=message["token"],
                        chat_id=message["chat_id"],
                        message_id=message["message_id"],
                        text=message["text"],
                        reply_markup=message["reply_markup"],
                    )
                )

                result = {
                    "id": message["id"],
                    "chat_id": message["chat_id"],
                    "message_id": str(
                        telegram_message.message_id
                    ),
                    "status": "edited",
                    "worker": worker_id,
                }

            # --------------------------------
            # RECREATE
            # --------------------------------

            elif message["action"] == "recreate":

                if message["message_id"]:

                    await telegram_service.delete_message(
                        token=message["token"],
                        chat_id=message["chat_id"],
                        message_id=message["message_id"],
                    )

                telegram_message = (
                    await telegram_service.send_message(
                        token=message["token"],
                        chat_id=message["chat_id"],
                        text=message["text"],
                        reply_markup=message["reply_markup"],
                    )
                )

                result = {
                    "id": message["id"],
                    "chat_id": message["chat_id"],
                    "message_id": str(
                        telegram_message.message_id
                    ),
                    "status": "sent",
                    "worker": worker_id,
                }

        except Exception as e:

            result = {
                "id": message["id"],
                "chat_id": message["chat_id"],
                "message_id": message.get("message_id"),
                "status": "failed",
                "error": str(e),
                "worker": worker_id,
            }

        finally:

            add_result(
                batch_id=batch_id,
                result=result,
            )

            message_queue.task_done()
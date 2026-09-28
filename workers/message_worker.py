from services.telegram.service import TelegramService
from workers.batch_manager import add_result
from workers.queue import message_queue
from database.connection import SessionLocal
from database.models import TelegramMessageState


telegram_service = TelegramService()


def get_state(
    db,
    message: dict,
) -> TelegramMessageState | None:
    return (
        db.query(TelegramMessageState)
        .filter(
            TelegramMessageState.django_message_id == message["id"]
        )
        .first()
    )


def save_message_state(
    db,
    message: dict,
    telegram_message_id: int,
    state: TelegramMessageState | None,
):
    if state is None:
        state = TelegramMessageState(
            django_message_id=message["id"],
            token=message["token"],
            chat_id=str(message["chat_id"]),
            telegram_message_id=telegram_message_id,
            reply_markup=message["reply_markup"],
            action=message["action"],
        )

        db.add(state)

    else:
        state.token = message["token"]
        state.chat_id = str(message["chat_id"])
        state.telegram_message_id = telegram_message_id
        state.reply_markup = message["reply_markup"]
        state.action = message["action"]

    db.commit()


async def message_worker(worker_id: int):

    while True:

        job = await message_queue.get()

        batch_id = job["batch_id"]
        message = job["message"]

        db = SessionLocal()

        try:

            # --------------------------------
            # GET STATE
            # --------------------------------

            state = get_state(
                db=db,
                message=message,
            )

            print(
                "state message:",
                state.telegram_message_id if state else None,
            )

            print(
                "message:",
                message.get("message_id"),
            )

            # --------------------------------
            # CHECK MESSAGE STATE
            # --------------------------------

            if (
                state
                and message.get("action") != "new"
                and str(state.telegram_message_id)
                != str(message.get("message_id"))
            ):
                print("message id changed -> recreate")

                message["action"] = "recreate"
                message["message_id"] = state.telegram_message_id

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

                save_message_state(
                    db=db,
                    state=state,
                    message=message,
                    telegram_message_id=telegram_message.message_id,
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

                save_message_state(
                    db=db,
                    state=state,
                    message=message,
                    telegram_message_id=telegram_message.message_id,
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

                old_message_id = message.get("message_id")

                if old_message_id:

                    await telegram_service.delete_message(
                        token=message["token"],
                        chat_id=message["chat_id"],
                        message_id=old_message_id,
                    )

                telegram_message = (
                    await telegram_service.send_message(
                        token=message["token"],
                        chat_id=message["chat_id"],
                        text=message["text"],
                        reply_markup=message["reply_markup"],
                    )
                )

                save_message_state(
                    db=db,
                    state=state,
                    message=message,
                    telegram_message_id=telegram_message.message_id,
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

            else:
                raise ValueError(
                    f"Unknown action: {message['action']}"
                )

        except Exception as e:

            db.rollback()

            result = {
                "id": message["id"],
                "chat_id": message["chat_id"],
                "message_id": message.get("message_id"),
                "status": "failed",
                "error": str(e),
                "worker": worker_id,
            }

        finally:

            db.close()

            add_result(
                batch_id=batch_id,
                result=result,
            )

            message_queue.task_done()
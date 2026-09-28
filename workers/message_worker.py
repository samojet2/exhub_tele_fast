import logging

from telegram.error import BadRequest, TimedOut

from services.telegram.service import TelegramService
from workers.batch_manager import add_result
from workers.queue import message_queue
from database.connection import SessionLocal
from database.models import TelegramMessageState


logger = logging.getLogger(__name__)

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
    """
    Create or update Telegram message state.
    """

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


async def recreate_message(
    message: dict,
):
    """
    Delete old message if possible and send a new one.

    Timeout during delete is treated as an unknown state.
    In that case we do NOT send a new message because the old
    message may actually have been deleted on Telegram.
    """

    old_message_id = message.get("message_id")

    # =================================
    # DELETE OLD MESSAGE
    # =================================

    if old_message_id:

        logger.info(
            "Deleting old Telegram message | "
            "chat_id=%s message_id=%s",
            message["chat_id"],
            old_message_id,
        )

        try:

            delete_response = (
                await telegram_service.delete_message(
                    token=message["token"],
                    chat_id=message["chat_id"],
                    message_id=old_message_id,
                )
            )

            logger.info(
                "Old Telegram message deleted | "
                "chat_id=%s message_id=%s response=%s",
                message["chat_id"],
                old_message_id,
                delete_response,
            )

        except TimedOut:

            logger.warning(
                "Timeout while deleting old Telegram message | "
                "chat_id=%s message_id=%s",
                message["chat_id"],
                old_message_id,
            )

            # VERY IMPORTANT:
            #
            # We don't know whether Telegram actually deleted
            # the message or not.
            #
            # Do not send a new message because it could create
            # a duplicate message.

            raise

        except BadRequest as e:

            logger.warning(
                "BadRequest while deleting old Telegram message | "
                "chat_id=%s message_id=%s error=%s",
                message["chat_id"],
                old_message_id,
                e,
            )

            # According to our current policy:
            #
            # BadRequest means the old message cannot be used.
            # Continue and send a new message.

        except Exception as e:

            logger.exception(
                "Unexpected error while deleting old Telegram message | "
                "chat_id=%s message_id=%s error=%s",
                message["chat_id"],
                old_message_id,
                e,
            )

            # According to our current policy:
            #
            # Any error except TimedOut allows us to continue
            # with sending the new message.

    # =================================
    # SEND NEW MESSAGE
    # =================================

    logger.info(
        "Sending recreated Telegram message | "
        "chat_id=%s django_message_id=%s",
        message["chat_id"],
        message["id"],
    )

    telegram_message = (
        await telegram_service.send_message(
            token=message["token"],
            chat_id=message["chat_id"],
            text=message["text"],
            reply_markup=message["reply_markup"],
        )
    )

    logger.info(
        "Recreated Telegram message sent | "
        "chat_id=%s message_id=%s django_message_id=%s",
        message["chat_id"],
        telegram_message.message_id,
        message["id"],
    )

    return telegram_message


async def message_worker(worker_id: int):

    while True:

        job = await message_queue.get()

        batch_id = job["batch_id"]
        message = job["message"]

        db = SessionLocal()
        result = None

        try:

            # =================================
            # GET CURRENT STATE
            # =================================

            state = get_state(
                db=db,
                message=message,
            )

            logger.info(
                "Processing Telegram message | "
                "worker=%s batch_id=%s django_message_id=%s "
                "db_message_id=%s incoming_message_id=%s action=%s",
                worker_id,
                batch_id,
                message["id"],
                state.telegram_message_id if state else None,
                message.get("message_id"),
                message["action"],
            )

            # =================================
            # CHECK STATE
            # =================================

            if (
                state
                and message.get("action") != "new"
                and message.get("message_id")
                and str(state.telegram_message_id)
                != str(message["message_id"])
            ):

                logger.warning(
                    "Telegram message_id mismatch -> recreate | "
                    "worker=%s django_message_id=%s "
                    "db_message_id=%s incoming_message_id=%s",
                    worker_id,
                    message["id"],
                    state.telegram_message_id,
                    message["message_id"],
                )

                message["action"] = "recreate"

                message["message_id"] = (
                    state.telegram_message_id
                )

            # =================================
            # NEW
            # =================================

            if message["action"] == "new":

                logger.info(
                    "Sending new Telegram message | "
                    "worker=%s django_message_id=%s chat_id=%s",
                    worker_id,
                    message["id"],
                    message["chat_id"],
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
                    telegram_message_id=(
                        telegram_message.message_id
                    ),
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

            # =================================
            # EDIT
            # =================================

            elif message["action"] == "edit":

                try:

                    logger.info(
                        "Editing Telegram message | "
                        "worker=%s django_message_id=%s "
                        "chat_id=%s message_id=%s",
                        worker_id,
                        message["id"],
                        message["chat_id"],
                        message["message_id"],
                    )

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
                        telegram_message_id=(
                            telegram_message.message_id
                        ),
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

                except TimedOut:

                    logger.warning(
                        "Timeout while editing Telegram message "
                        "-> recreate skipped | "
                        "worker=%s django_message_id=%s "
                        "chat_id=%s message_id=%s",
                        worker_id,
                        message["id"],
                        message["chat_id"],
                        message["message_id"],
                    )

                    # We don't know whether Telegram processed
                    # the edit or not.
                    #
                    # Do NOT recreate.
                    raise

                except BadRequest as e:

                    logger.warning(
                        "BadRequest while editing Telegram message "
                        "-> recreate | "
                        "worker=%s django_message_id=%s "
                        "chat_id=%s message_id=%s error=%s",
                        worker_id,
                        message["id"],
                        message["chat_id"],
                        message["message_id"],
                        e,
                    )

                    message["action"] = "recreate"

                    telegram_message = (
                        await recreate_message(
                            message=message,
                        )
                    )

                    save_message_state(
                        db=db,
                        state=state,
                        message=message,
                        telegram_message_id=(
                            telegram_message.message_id
                        ),
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

                    logger.exception(
                        "Unexpected edit error "
                        "-> recreate | "
                        "worker=%s django_message_id=%s "
                        "chat_id=%s message_id=%s error=%s",
                        worker_id,
                        message["id"],
                        message["chat_id"],
                        message["message_id"],
                        e,
                    )

                    message["action"] = "recreate"

                    telegram_message = (
                        await recreate_message(
                            message=message,
                        )
                    )

                    save_message_state(
                        db=db,
                        state=state,
                        message=message,
                        telegram_message_id=(
                            telegram_message.message_id
                        ),
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

            # =================================
            # RECREATE
            # =================================

            elif message["action"] == "recreate":

                logger.info(
                    "Recreating Telegram message | "
                    "worker=%s django_message_id=%s "
                    "chat_id=%s old_message_id=%s",
                    worker_id,
                    message["id"],
                    message["chat_id"],
                    message.get("message_id"),
                )

                telegram_message = (
                    await recreate_message(
                        message=message,
                    )
                )

                save_message_state(
                    db=db,
                    state=state,
                    message=message,
                    telegram_message_id=(
                        telegram_message.message_id
                    ),
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

            # =================================
            # UNKNOWN ACTION
            # =================================

            else:

                raise ValueError(
                    f"Unknown action: {message['action']}"
                )

        except Exception as e:

            db.rollback()

            logger.exception(
                "Telegram message processing failed | "
                "worker=%s batch_id=%s django_message_id=%s "
                "chat_id=%s action=%s error=%s",
                worker_id,
                batch_id,
                message.get("id"),
                message.get("chat_id"),
                message.get("action"),
                e,
            )

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

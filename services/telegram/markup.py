from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_reply_markup(data):
    if not data:
        return None

    keyboard = []

    for row in data:
        buttons = []

        for button in row:
            kwargs = {
                "text": button["text"],
            }

            if button.get("url"):
                kwargs["url"] = button["url"]

            elif button.get("callback_data"):
                kwargs["callback_data"] = button["callback_data"]

            buttons.append(
                InlineKeyboardButton(**kwargs)
            )

        keyboard.append(buttons)

    return InlineKeyboardMarkup(keyboard)
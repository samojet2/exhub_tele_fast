from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


def build_reply_markup(data):
    if not data:
        return None

    keyboard = [
        [
            InlineKeyboardButton(
                text=button["text"],
                callback_data=button.get("callback_data"),
            )
            for button in row
        ]
        for row in data
    ]

    return InlineKeyboardMarkup(keyboard)
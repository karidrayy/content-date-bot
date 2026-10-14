import asyncio
import html
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS = {
    int(item.strip())
    for item in ADMIN_IDS_RAW.split(",")
    if item.strip().isdigit()
}

WELCOME_TEXT = (
    "Привет! Это бот-предложка проекта CONTENT DATE❤️\n\n"
    "Если у вас есть идея для мероприятия, предложение о съёмке или вас "
    "просто беспокоит какой-то вопрос — смело пишите в нашего бота, "
    "а мы постараемся ответить как можно скорее💌"
)

if not BOT_TOKEN:
    raise RuntimeError("Не задана переменная окружения BOT_TOKEN.")
if not ADMIN_IDS:
    raise RuntimeError(
        "Не заданы ADMIN_IDS. Укажите Telegram ID администраторов через запятую."
    )

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

# Связь между уведомлениями в чате администратора и автором сообщения.
# Хранится в памяти процесса; после перезапуска старые уведомления не будут доступны для ответа.
message_recipients: dict[tuple[int, int], int] = {}


@dp.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        WELCOME_TEXT
        + "\n\nНапишите следующим сообщением вашу идею или вопрос — "
        "мы передадим его команде CONTENT DATE❤️"
    )


@dp.message(F.from_user)
async def receive_message(message: Message) -> None:
    user = message.from_user
    if user is None:
        return

    # Администратор отвечает реплаем на уведомление или скопированное сообщение.
    if user.id in ADMIN_IDS:
        if message.reply_to_message:
            key = (message.chat.id, message.reply_to_message.message_id)
            recipient_id = message_recipients.get(key)

            if recipient_id is None:
                # Запасной вариант: прочитать ID из текста уведомления.
                original_text = (
                    message.reply_to_message.text
                    or message.reply_to_message.caption
                    or ""
                )
                marker = "USER_ID:"
                if marker in original_text:
                    try:
                        recipient_id = int(
                            original_text.split(marker, 1)[1].split()[0]
                        )
                    except (ValueError, IndexError):
                        recipient_id = None

            if recipient_id is None:
                await message.reply(
                    "Не нашёл автора этого сообщения. Ответьте реплаем на новое уведомление бота."
                )
                return

            try:
                await bot.send_message(
                    recipient_id,
                    "Ответ от команды CONTENT DATE❤️\n\n"
                    + (message.text or message.caption or "Администратор отправил вам сообщение."),
                )
                await message.reply("Ответ отправлен пользователю ✅")
            except Exception:
                logging.exception("Не удалось отправить ответ пользователю")
                await message.reply(
                    "Не удалось доставить ответ. Возможно, пользователь ещё не запускал бота."
                )
        return

    if message.text and message.text.startswith("/"):
        return

    if not (
        message.text or message.caption or message.photo or message.document
        or message.video or message.voice or message.audio or message.animation
        or message.sticker
    ):
        await message.answer("Пожалуйста, отправьте текст, фото, видео или файл 💌")
        return

    full_name = html.escape(
        " ".join(part for part in [user.first_name, user.last_name] if part)
        or "Имя не указано"
    )
    username = html.escape(f"@{user.username}" if user.username else "не указан")

    header = (
        "💌 <b>Новое сообщение — CONTENT DATE</b>\n"
        f"<b>От:</b> {full_name}\n"
        f"<b>Username:</b> {username}\n"
        f"<b>USER_ID:</b> {user.id}\n"
        "<i>Чтобы ответить, нажмите «Ответить» на этом уведомлении или на сообщении ниже.</i>"
    )

    delivered = 0
    for admin_id in ADMIN_IDS:
        try:
            header_message = await bot.send_message(admin_id, header)
            message_recipients[(admin_id, header_message.message_id)] = user.id

            copied_message = await bot.copy_message(
                chat_id=admin_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
            message_recipients[(admin_id, copied_message.message_id)] = user.id
            delivered += 1
        except Exception:
            logging.exception("Не удалось доставить сообщение администратору %s", admin_id)

    if delivered:
        await message.answer("Спасибо! Ваше сообщение передано команде CONTENT DATE❤️💌")
    else:
        await message.answer(
            "Не получилось доставить сообщение команде. Попробуйте немного позже 🙏"
        )


async def main() -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

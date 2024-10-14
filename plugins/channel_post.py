import asyncio
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from bot import Bot
from config import ADMINS, CHANNEL_ID, DISABLE_CHANNEL_BUTTON, LOGGER
from utils.helpers import encode

# Handler untuk menangani forward pesan dari admin dan membuat link secara otomatis
@Bot.on_message(
    filters.private
    & filters.user(ADMINS)
    & ~filters.command(
        [
            "start",
            "users",
            "broadcast",
            "ping",
            "edit",
            "uptime",
            "batch",
            "logs",
            "genlink",
        ]
    )
)
async def forward_to_channel(client: Client, message: Message):
    # Tampilkan pesan sementara saat proses berlangsung
    temp_msg = await message.reply_text("<code>Memproses pesan...</code>", quote=True)

    # Mencoba untuk menyalin pesan ke channel database
    try:
        forwarded_msg = await message.copy(chat_id=client.db_channel.id, disable_notification=True)
    except FloodWait as e:
        await asyncio.sleep(e.x)
        forwarded_msg = await message.copy(chat_id=client.db_channel.id, disable_notification=True)
    except Exception as err:
        LOGGER(__name__).warning(err)
        await temp_msg.edit_text("<b>Error saat memproses pesan...</b>")
        return

    # Membuat link sharing
    msg_id = forwarded_msg.id * abs(client.db_channel.id)
    encoded_string = f"get-{msg_id}"
    link = f"https://t.me/{client.username}?start={encode(encoded_string)}"

    # Membuat tombol share link
    buttons = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔁 Bagikan Link", url=f"https://telegram.me/share/url?url={link}")]]
    )

    # Edit pesan sementara dengan link yang dibuat
    await temp_msg.edit(
        f"<b>Link Berhasil Dibuat:</b>\n\n{link}",
        reply_markup=buttons,
        disable_web_page_preview=True,
    )

    # Menambahkan tombol share ke pesan yang dikirim di channel database (jika diaktifkan)
    if not DISABLE_CHANNEL_BUTTON:
        try:
            await forwarded_msg.edit_reply_markup(buttons)
        except Exception:
            pass


# Handler untuk membuat link secara otomatis ketika ada post baru di channel database
@Bot.on_message(filters.channel & filters.incoming & filters.chat(CHANNEL_ID))
async def auto_post(client: Client, message: Message):
    # Jika tombol channel dinonaktifkan, hentikan proses
    if DISABLE_CHANNEL_BUTTON:
        return

    # Buat link sharing otomatis
    msg_id = message.id * abs(client.db_channel.id)
    encoded_string = f"get-{msg_id}"
    link = f"https://t.me/{client.username}?start={encode(encoded_string)}"

    # Membuat tombol share link
    buttons = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔁 Bagikan Link", url=f"https://telegram.me/share/url?url={link}")]]
    )

    # Edit pesan dengan menambahkan tombol share link
    try:
        await message.edit_reply_markup(buttons)
    except Exception:
        pass

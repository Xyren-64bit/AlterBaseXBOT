# (©)Codexbotz
# Recode by @mrismanaziz
# t.me/SharingUserbot & t.me/Lunatic0de

import os
import subprocess
import sys
import asyncio
from dotenv import load_dotenv, set_key
from datetime import datetime, timedelta
from pytz import timezone

from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from pyrogram.types import Message
from bot import Bot 
from config import ADMINS, LOGGER
from database.sql import query_msg, delete_user
from helper_func import get_message_id


@Bot.on_message(filters.command("edit") & filters.user(ADMINS))
async def edit_variable(client: Bot, message: Message):
    """Edit variables in config.env."""

    cmd = message.text.split(" ", 2)
    if len(cmd) < 3:
        return await message.reply_text("Format salah! Gunakan: /edit VARIABEL nilai")

    var_name, new_value = cmd[1], cmd[2]

    # Check if the variable exists in config.env
    if var_name not in os.environ:
        return await message.reply_text(f"Variabel {var_name} tidak ditemukan dalam config.env")

    # Update the variable in config.env
    set_key("config.env", var_name, new_value)

    await message.reply_text(
        f"Berhasil mengubah nilai variabel {var_name} menjadi {new_value}.\n"
        "Gunakan perintah /restart untuk menerapkan perubahan."
    )


@Bot.on_message(filters.command("restart") & filters.user(ADMINS))
async def restart_bot(client: Bot, message: Message):
    """Performs a hard restart of the bot."""

    restart_message = await message.reply_text("<b>Melakukan hard restart...</b>")

    load_dotenv("config.env", override=True) 
    
    del sys.modules["config"]

    async def restart_task():
        try:
            await asyncio.wait_for(client.stop(), timeout=10)
        except asyncio.TimeoutError:
            LOGGER(__name__).warning("Penghentian bot timeout. Memaksa keluar.")
        finally:
            LOGGER(__name__).info("Restarting bot...")
            subprocess.Popen([sys.executable, "main.py"])

    asyncio.create_task(restart_task())

    await asyncio.sleep(5)
    await restart_message.edit("✅ Proses restart selesai. Bot berhasil diaktifkan kembali.")


@Bot.on_message(filters.command("post") & filters.user(ADMINS))
async def schedule_post(client: Bot, message: Message):
    """
    Schedules a message to be reposted at a specified time (WIB) and broadcasts it to all users.
    Supports two formats:
    - /post jam:menit
    - /post tanggal/bulan/tahun jam:menit
    """

    if not message.reply_to_message:
        return await message.reply_text("<b>Balas ke pesan yang ingin dijadwalkan.</b>")

    if len(message.command) < 2:
        return await message.reply_text("<b>Format salah!</b> Gunakan:\n- `/post jam:menit` (dalam WIB)\n- `/post tanggal/bulan/tahun jam:menit` (dalam WIB)")

    try:
        scheduled_time_str = message.command[1]
        if "/" in scheduled_time_str:  # Format dengan tanggal
            date_str, time_str = scheduled_time_str.split(" ")
            scheduled_day, scheduled_month, scheduled_year = map(int, date_str.split("/"))
            scheduled_hour, scheduled_minute = map(int, time_str.split(":"))
            scheduled_time = datetime(scheduled_year, scheduled_month, scheduled_day, scheduled_hour, scheduled_minute, tzinfo=timezone('Asia/Jakarta'))
        else:  # Format hanya jam
            scheduled_hour, scheduled_minute = map(int, scheduled_time_str.split(":"))
            now = datetime.now(timezone('Asia/Jakarta'))
            if scheduled_hour < now.hour or (scheduled_hour == now.hour and scheduled_minute <= now.minute):
                scheduled_time = now.replace(hour=scheduled_hour, minute=scheduled_minute, second=0, microsecond=0) + timedelta(days=1)
            else:
                scheduled_time = now.replace(hour=scheduled_hour, minute=scheduled_minute, second=0, microsecond=0)

        if scheduled_hour < 0 or scheduled_hour > 23:
            raise ValueError("Jam tidak valid. Harus antara 0 dan 23.")
        if scheduled_minute < 0 or scheduled_minute > 59:
            raise ValueError("Menit tidak valid. Harus antara 0 dan 59.")

        now = datetime.now(timezone('Asia/Jakarta'))
        delay = (scheduled_time - now).total_seconds()

        await message.reply_text(f"Pesan akan diposting ulang dan dibroadcast pada {scheduled_time.strftime('%d/%m/%Y %H:%M')} WIB.")

        await asyncio.sleep(delay)

        # Broadcast pesan ke semua pengguna
        query = await query_msg()
        broadcast_msg = message.reply_to_message
        total = 0
        successful = 0
        blocked = 0
        deleted = 0
        unsuccessful = 0

        pls_wait = await message.reply(

            "<code>Broadcasting Message Tunggu Sebentar...</code>"
        )
        for row in query:
            chat_id = int(row[0])

            if chat_id not in ADMINS:
                try:
                    await broadcast_msg.copy(chat_id)
                    successful += 1
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    await broadcast_msg.copy(chat_id)

                    successful += 1
                except UserIsBlocked:

                    await delete_user(chat_id)
                    blocked += 1
                except InputUserDeactivated:
                    await delete_user(chat_id)
                    deleted += 1
                except BaseException:
                    unsuccessful += 1
                total += 1

        status = f"""<b><u>Berhasil Broadcast</u>
Jumlah Pengguna: <code>{total}</code>

Berhasil: <code>{successful}</code>
Gagal: <code>{unsuccessful}</code>
Pengguna diblokir: <code>{blocked}</code>
Akun Terhapus: <code>{deleted}</code></b>"""

        await pls_wait.edit(status)

    except ValueError as e:
        await message.reply_text(str(e))
        

@Bot.on_message(filters.command("config") & filters.user(ADMINS))
async def send_config_file(client: Bot, message: Message):
    """Sends the config.env file to the admin."""
    if os.path.exists("config.env"):
        try:
            await message.reply_document("config.env")
        except Exception as e:
            LOGGER(__name__).warning(e)
            await message.reply_text("❌ <b>Error saat mengirim file config.env!</b>")
    else:
        await message.reply_text("❌ <b>File config.env tidak ditemukan!</b>")

@Bot.on_message(filters.command("delete") & filters.user(ADMINS))
async def delete_link(client: Bot, message: Message):
    """Deletes a message from the database channel, effectively removing its share link."""

    if len(message.command) < 2:
        return await message.reply_text("<b>Silahkan berikan link pesan dari Channel ID Database untuk menghapusnya.</b>")

    # Ambil link dari argumen perintah
    message_link = message.command[1]

    # Ekstrak ID pesan dari link
    msg_id = await get_message_id(client, Message(text=message_link))  # Buat objek Message dummy untuk get_message_id
    if not msg_id:
        return await message.reply_text("<b>Link yang Anda berikan tidak valid atau bukan dari Channel ID Database.</b>")

    try:
        await client.delete_messages(chat_id=CHANNEL_ID, message_ids=msg_id)
        await message.reply_text("✅ <b>Pesan berhasil dihapus dari Channel ID Database. Link berbagi tidak lagi valid.</b>")
    except Exception as e:
        LOGGER(__name__).error(f"Error saat menghapus pesan: {e}")
        await message.reply_text("❌ <b>Terjadi kesalahan saat menghapus pesan. Silakan coba lagi nanti.</b>")

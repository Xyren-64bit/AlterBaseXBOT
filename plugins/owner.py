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

    restart_message = await message.reply_text("**Melakukan hard restart...**")

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
    Schedules a message to be reposted at a specified hour and minute (WIB).
    """

    if not message.reply_to_message:
        return await message.reply_text("**Balas ke pesan yang ingin dijadwalkan.**")

    if len(message.command) == 1:
        return await message.reply_text("**Format salah!** Gunakan: `/post jam:menit` (dalam WIB)")

    try:
        scheduled_time_str = message.command[1]
        scheduled_hour, scheduled_minute = map(int, scheduled_time_str.split(":"))

        if scheduled_hour < 0 or scheduled_hour > 23:
            raise ValueError("Jam tidak valid. Harus antara 0 dan 23.")
        if scheduled_minute < 0 or scheduled_minute > 59:
            raise ValueError("Menit tidak valid. Harus antara 0 dan 59.")

        now = datetime.now(timezone('Asia/Jakarta'))

        if scheduled_hour < now.hour or (scheduled_hour == now.hour and scheduled_minute <= now.minute):

            scheduled_time = now.replace(hour=scheduled_hour, minute=scheduled_minute, second=0, microsecond=0) + timedelta(days=1)
        else:
     
            scheduled_time = now.replace(hour=scheduled_hour, minute=scheduled_minute, second=0, microsecond=0)

        delay = (scheduled_time - now).total_seconds()

        await message.reply_text(f"Pesan akan diposting ulang pada pukul {scheduled_hour:02d}:{scheduled_minute:02d} WIB.")

        await asyncio.sleep(delay)
        
        await message.reply_to_message.copy(message.chat.id)

    except ValueError as e:
        await message.reply_text(str(e))

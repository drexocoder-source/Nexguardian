import sqlite3
import asyncio
from collections import defaultdict
from telegram import Update
from telegram.ext import ContextTypes

# -----------------------------
# DATABASE
# -----------------------------
def init_media_db():
    """Create media settings table if not exists."""
    conn = sqlite3.connect("nexora_guardian.db")
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS media_settings
           (chat_id INTEGER PRIMARY KEY,
            is_enabled INTEGER DEFAULT 0,
            interval_seconds INTEGER DEFAULT 1800)"""
    )
    conn.commit()
    conn.close()

def get_media_settings(chat_id: int):
    """Return media settings for a chat."""
    try:
        conn = sqlite3.connect("nexora_guardian.db")
        c = conn.cursor()
        c.execute(
            "SELECT is_enabled, interval_seconds FROM media_settings WHERE chat_id = ?",
            (chat_id,),
        )
        result = c.fetchone()
        if result:
            return {"is_enabled": bool(result[0]), "interval_seconds": result[1]}
        # default: disabled, 30 minutes
        return {"is_enabled": False, "interval_seconds": 1800}
    finally:
        conn.close()

def update_media_settings(chat_id: int, is_enabled=None, interval_minutes=None):
    """Update media settings. Interval is provided in minutes."""
    current = get_media_settings(chat_id)
    enabled = int(is_enabled if is_enabled is not None else current["is_enabled"])
    interval_seconds = interval_minutes * 60 if interval_minutes is not None else current["interval_seconds"]

    conn = sqlite3.connect("nexora_guardian.db")
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO media_settings (chat_id, is_enabled, interval_seconds) VALUES (?, ?, ?)",
        (chat_id, enabled, interval_seconds)
    )
    conn.commit()
    conn.close()

# -----------------------------
# MEDIA HANDLER
# -----------------------------
media_queue = defaultdict(list)  # chat_id -> list of messages
DEFAULT_INTERVAL_MIN = 30  # default 30 minutes

async def media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.chat:
        return

    chat_id = message.chat.id
    settings = get_media_settings(chat_id)
    if not settings["is_enabled"]:
        return

    # Only media types
    if not any([message.photo, message.video, message.animation, message.sticker]):
        return

    # Add to queue
    media_queue[chat_id].append(message)

    # Start batch task if not running
    if not hasattr(context.application, f"media_task_{chat_id}"):
        interval_minutes = settings["interval_seconds"] // 60
        setattr(context.application, f"media_task_{chat_id}", True)
        asyncio.create_task(process_media_batch(chat_id, context, interval_minutes * 60))

async def process_media_batch(chat_id, context: ContextTypes.DEFAULT_TYPE, interval_seconds: int):
    """Delete all queued media messages after the interval."""
    await asyncio.sleep(interval_seconds)

    messages = media_queue.pop(chat_id, [])
    deleted_count = 0

    for msg in messages:
        try:
            await msg.delete()
            deleted_count += 1
        except:
            pass

    if deleted_count > 0:
        try:
            summary = await context.bot.send_message(chat_id, f"🗑️ Deleted {deleted_count} media messages")
            await asyncio.sleep(3)
            await summary.delete()
        except:
            pass

    # Reset task flag
    setattr(context.application, f"media_task_{chat_id}", False)

# -----------------------------
# COMMANDS (Admin Only)
# -----------------------------
async def media_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enable/disable media auto-delete or show status (admins only)."""
    message = update.message
    chat = message.chat
    user = message.from_user

    # Check if user is admin
    member = await chat.get_member(user.id)
    if not member.status in ["administrator", "creator"]:
        await message.reply_text("⚠️ Only group admins can use this command.")
        return

    chat_id = chat.id
    args = message.text.split()

    if len(args) == 1:
        settings = get_media_settings(chat_id)
        status = "enabled ✅" if settings["is_enabled"] else "disabled ❌"
        interval_min = settings["interval_seconds"] // 60
        await message.reply_text(f"🗑️ Media auto-delete is {status}\n⏱ Interval: {interval_min} minutes")
        return

    if args[1].lower() in ["on", "off"]:
        enabled = args[1].lower() == "on"
        update_media_settings(chat_id, is_enabled=enabled)
        status = "enabled ✅" if enabled else "disabled ❌"
        await message.reply_text(f"🗑️ Media auto-delete {status}")
    else:
        await message.reply_text("Usage: /media on|off")


async def interval_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set or view the media deletion interval in minutes (admins only)."""
    message = update.message
    chat = message.chat
    user = message.from_user

    # Check if user is admin
    member = await chat.get_member(user.id)
    if not member.status in ["administrator", "creator"]:
        await message.reply_text("⚠️ Only group admins can use this command.")
        return

    chat_id = chat.id
    args = message.text.split()

    if len(args) == 1:
        settings = get_media_settings(chat_id)
        interval_min = settings["interval_seconds"] // 60
        await message.reply_text(f"⏱ Current media deletion interval: {interval_min} minutes")
        return

    if args[1].isdigit():
        interval_min = int(args[1])
        update_media_settings(chat_id, interval_minutes=interval_min)
        await message.reply_text(f"⏱ Media deletion interval set to {interval_min} minutes")
    else:
        await message.reply_text("Usage: /interval <minutes>")

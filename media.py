import sqlite3
import asyncio
from collections import defaultdict
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
DB_FILE = "nexora_guardian.db"
UPDATES_LINK = "https://t.me/Nexxxxxo_bots"

# -----------------------------
# DATABASE
# -----------------------------
def init_media_db():
    conn = sqlite3.connect(DB_FILE)
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
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute(
            "SELECT is_enabled, interval_seconds FROM media_settings WHERE chat_id = ?",
            (chat_id,),
        )
        row = c.fetchone()
        if row:
            return {"is_enabled": bool(row[0]), "interval_seconds": row[1]}
        return {"is_enabled": False, "interval_seconds": 1800}
    finally:
        conn.close()


def update_media_settings(chat_id: int, is_enabled=None, interval_minutes=None):
    current = get_media_settings(chat_id)
    enabled = int(is_enabled if is_enabled is not None else current["is_enabled"])
    interval_seconds = (
        interval_minutes * 60 if interval_minutes is not None else current["interval_seconds"]
    )

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO media_settings (chat_id, is_enabled, interval_seconds) VALUES (?, ?, ?)",
        (chat_id, enabled, interval_seconds)
    )
    conn.commit()
    conn.close()

# -----------------------------
# MEDIA HANDLER (FIXED)
# -----------------------------
media_queue = defaultdict(list)
media_tasks = {}  # chat_id -> asyncio.Task


async def media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.chat:
        return

    chat = message.chat
    if chat.type not in ["group", "supergroup"]:
        return

    settings = get_media_settings(chat.id)
    if not settings["is_enabled"]:
        return

    is_media = any([
        message.photo,
        message.video,
        message.animation,
        message.sticker,
        message.document and message.document.mime_type == "video/mp4"
    ])

    if not is_media:
        return

    # Add to queue
    media_queue[chat.id].append(message)

    # Start task if not already running
    if chat.id not in media_tasks:
        task = asyncio.create_task(
            process_media_batch(chat.id, context, settings["interval_seconds"])
        )
        media_tasks[chat.id] = task


async def process_media_batch(chat_id, context: ContextTypes.DEFAULT_TYPE, interval_seconds: int):
    await asyncio.sleep(interval_seconds)

    messages = media_queue.pop(chat_id, [])
    deleted_count = 0

    for msg in messages:
        try:
            await msg.delete()
            deleted_count += 1
        except:
            pass  # no rights / already deleted

    # Send summary (no HTML, no parse errors)
    if deleted_count > 0:
        try:
            summary = await context.bot.send_message(
                chat_id,
                f"🗑️ {deleted_count} media messages were auto-deleted."
            )
            await asyncio.sleep(3)
            await summary.delete()
        except:
            pass

    # Clear task
    media_tasks.pop(chat_id, None)

    
# -----------------------------
# COMMANDS
# -----------------------------
async def media_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat = message.chat
    user = message.from_user

    # Block in DM
    if chat.type == "private":
        await message.reply_text("🚫 This command works only in groups.")
        return

    # Check user admin
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status not in ["administrator", "creator"]:
            await message.reply_text("⚠️ Only group admins can use this command.")
            return
    except Exception:
        await message.reply_text(
            "❌ I can't verify your admin status.\n"
            "Please make sure I'm an admin in this group."
        )
        return

    # Check bot permissions
    try:
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        can_delete = bot_member.can_delete_messages
    except Exception:
        await message.reply_text(
            "❌ I need admin rights to work.\n"
            "Please promote me with:\n"
            "• Delete messages"
        )
        return

    args = message.text.split()
    settings = get_media_settings(chat.id)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Updates", url=UPDATES_LINK)]
    ])

    if len(args) == 1:
        status = "enabled ✅" if settings["is_enabled"] else "disabled ❌"
        interval_min = settings["interval_seconds"] // 60
        await message.reply_text(
            f"🗑️ Media Auto-Delete\n\n"
            f"Status: {status}\n"
            f"Interval: {interval_min} minutes",
            reply_markup=keyboard
        )
        return

    if args[1].lower() in ["on", "off"]:
        enabled = args[1].lower() == "on"

        if enabled and not can_delete:
            await message.reply_text(
                "❌ I need Delete Messages permission to work.\n\n"
                "Please give me:\n"
                "• Delete messages\n\n"
                "Then try again: /media on"
            )
            return

        update_media_settings(chat.id, is_enabled=enabled)
        status = "enabled ✅" if enabled else "disabled ❌"
        await message.reply_text(
            f"🗑️ Media auto-delete {status}",
            reply_markup=keyboard
        )
    else:
        await message.reply_text("Usage: /media on|off")


async def interval_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat = message.chat
    user = message.from_user

    if chat.type == "private":
        await message.reply_text("🚫 This command works only in groups.")
        return

    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status not in ["administrator", "creator"]:
            await message.reply_text("⚠️ Only group admins can use this command.")
            return
    except Exception:
        await message.reply_text("❌ I can't verify your admin status.")
        return

    args = message.text.split()
    settings = get_media_settings(chat.id)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Updates", url=UPDATES_LINK)]
    ])

    if len(args) == 1:
        interval_min = settings["interval_seconds"] // 60
        await message.reply_text(
            f"⏱ Current media deletion interval: {interval_min} minutes",
            reply_markup=keyboard
        )
        return

    if args[1].isdigit():
        interval_min = int(args[1])
        update_media_settings(chat.id, interval_minutes=interval_min)
        await message.reply_text(
            f"⏱ Media deletion interval set to {interval_min} minutes",
            reply_markup=keyboard
        )
    else:
        await message.reply_text("Usage: /interval <minutes>")

from telegram import Update
from telegram.ext import ContextTypes
import sqlite3
import asyncio

# ======================
# DATABASE
# ======================
def init_edit_db():
    """Create the table if it doesn't exist."""
    try:
        conn = sqlite3.connect("nexora_guardian.db")
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS edit_settings
               (chat_id INTEGER PRIMARY KEY,
                is_enabled INTEGER DEFAULT 0,
                delay_seconds INTEGER DEFAULT 5)"""
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error in init_edit_db: {e}")
    finally:
        conn.close()


def get_edit_settings(chat_id: int):
    try:
        conn = sqlite3.connect("nexora_guardian.db")
        c = conn.cursor()
        c.execute(
            "SELECT is_enabled, delay_seconds FROM edit_settings WHERE chat_id = ?",
            (chat_id,),
        )
        result = c.fetchone()
        if result:
            return {"is_enabled": bool(result[0]), "delay_seconds": result[1]}
        return {"is_enabled": False, "delay_seconds": 5}
    except sqlite3.Error as e:
        print(f"Database error in get_edit_settings: {e}")
        return {"is_enabled": False, "delay_seconds": 5}
    finally:
        conn.close()


def update_edit_settings(chat_id: int, is_enabled=None, delay_seconds=None):
    """Update or insert group edit settings."""
    current = get_edit_settings(chat_id)
    enabled = int(is_enabled if is_enabled is not None else current["is_enabled"])
    delay = delay_seconds if delay_seconds is not None else current["delay_seconds"]

    try:
        conn = sqlite3.connect("nexora_guardian.db")
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO edit_settings (chat_id, is_enabled, delay_seconds) VALUES (?, ?, ?)",
            (chat_id, enabled, delay),
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error in update_edit_settings: {e}")
    finally:
        conn.close()

# ======================
# ADMIN HELPERS
# ======================
async def get_admins(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Return a list of admin user IDs in a chat."""
    admins = []
    try:
        members = await context.bot.get_chat_administrators(chat_id)
        admins = [m.user.id for m in members]
    except Exception as e:
        print(f"Error fetching admins for chat {chat_id}: {e}")
    return admins


async def is_admin(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int):
    """Check if a user is admin."""
    admins = await get_admins(context, chat_id)
    return user_id in admins

# ======================
# EDIT DEFENDER
# ======================
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

async def on_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Trigger when a message is edited.
    Deletes the message if edit defender is enabled and user is not admin.
    """
    message = update.edited_message
    try:
        if not message or message.chat.type not in ["group", "supergroup"]:
            return
        if not message.from_user:
            print(f"[EDIT DEBUG] Skipping message with no user. ChatID: {message.chat.id}")
            return

        text = message.text or "<no text>"
        user = message.from_user.username or message.from_user.first_name
        print(f"[EDIT DEBUG] ChatID: {message.chat.id}, User: {user}, Text: {text}")

        # Fetch settings from DB
        settings = get_edit_settings(message.chat.id)
        if not settings["is_enabled"] or settings["delay_seconds"] <= 0:
            print(f"[EDIT DEBUG] Edit defender disabled or delay <= 0 for chat {message.chat.id}")
            return

        # Skip admins
        if await is_admin(context.bot, message.chat.id, message.from_user.id):
            print(f"[EDIT DEBUG] Skipping admin: {user}")
            return

        # Send warning
        warning_text = (
            f"⚠️ Edit Alert!\n"
            f"🚫 Edits are not allowed in this group!\n"
            f"⏳ Your message will be deleted in {settings['delay_seconds']} seconds."
        )
        try:
            sent = await message.reply_text(warning_text)
        except Exception as e:
            print(f"[EDIT DEBUG] Cannot send warning message: {e}")
            sent = None

        # Wait delay
        await asyncio.sleep(settings["delay_seconds"])

        # Delete original edited message
        try:
            await context.bot.delete_message(message.chat.id, message.message_id)
            print(f"[EDIT DEBUG] Deleted edited message from {user}")
        except Exception as e:
            print(f"[EDIT DEBUG] Cannot delete message: {e}")

        # Delete warning
        if sent:
            try:
                await sent.delete()
            except Exception as e:
                print(f"[EDIT DEBUG] Cannot delete warning message: {e}")

    except Exception as e:
        print(f"[EDIT DEBUG] Error in on_edit: {e}")

# ======================
async def setdelay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message.chat.type == "private":
        await message.reply_text("🚫 This command works only in groups.")
        return

    if not await is_admin(context, message.chat.id, message.from_user.id):
        await message.reply_text("⚠️ Only admins can use this command.")
        return

    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        await message.reply_text("ℹ️ Usage: `/setdelay <seconds>`", parse_mode="Markdown")
        return

    delay = int(args[1])
    update_edit_settings(message.chat.id, delay_seconds=delay)
    await message.reply_text(f"⏳ Edit delay set to {delay} seconds.")

async def editdefender_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message.chat.type == "private":
        await message.reply_text("🚫 This command works only in groups.")
        return

    if not await is_admin(context, message.chat.id, message.from_user.id):
        await message.reply_text("⚠️ Only admins can use this command.")
        return

    args = message.text.split()
    current = get_edit_settings(message.chat.id)

    if len(args) == 1:
        status = "enabled ✅" if current["is_enabled"] else "disabled ❌"
        delay = current["delay_seconds"]
        await message.reply_text(f"🛡️ Edit Defender is {status}\n⏳ Delay: {delay} seconds")
        return

    if args[1].lower() not in ["on", "off"]:
        await message.reply_text("ℹ️ Usage: `/editedit on/off`")
        return

    enabled = args[1].lower() == "on"
    update_edit_settings(message.chat.id, is_enabled=enabled)
    status = "enabled ✅" if enabled else "disabled ❌"
    await message.reply_text(f"🛡️ Edit Defender {status} for this group.")

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    chat_id = message.chat.id if message.chat else None

    if message.chat.type == "private":
        await message.reply_text(f"🆔 Your User ID: `{user_id}`", parse_mode="Markdown")
    else:
        await message.reply_text(
            f"👤 User ID: `{user_id}`\n👥 Group ID: `{chat_id}`",
            parse_mode="Markdown"
        )

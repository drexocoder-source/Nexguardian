from telegram import Update
from telegram.ext import ContextTypes
import sqlite3
import asyncio

UPDATES_LINK = "https://t.me/Nexxxxxo_bots"


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
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except Exception:
        return False

# ======================
# BACKGROUND DELETION
# ======================
async def delete_later(bot, chat_id, msg_id, warning, delay, user):
    """Delete the edited message + warning after delay (background)."""
    try:
        await asyncio.sleep(delay)

        # Delete edited message
        try:
            await bot.delete_message(chat_id, msg_id)
            print(f"[EDIT DEBUG] Deleted edited message from {user}")
        except Exception as e:
            print(f"[EDIT DEBUG] Cannot delete message: {e}")

        # Delete warning
        if warning:
            try:
                await warning.delete()
            except Exception as e:
                print(f"[EDIT DEBUG] Cannot delete warning message: {e}")

    except Exception as e:
        print(f"[EDIT DEBUG] Error in delete_later: {e}")

from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from telegram import InlineKeyboardMarkup, InlineKeyboardButton

async def on_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.edited_message
    try:
        if not message or message.chat.type not in ["group", "supergroup"]:
            return
        if not message.from_user:
            return

        # Check bot delete rights
        try:
            bot_member = await context.bot.get_chat_member(
                message.chat.id, context.bot.id
            )
            if not bot_member.can_delete_messages:
                return
        except Exception:
            return

        settings = get_edit_settings(message.chat.id)
        if not settings["is_enabled"] or settings["delay_seconds"] <= 0:
            return

        user = message.from_user.mention_html()
        delay = settings["delay_seconds"]

        warning_text = (
            f"🛡️ <b>Edit Defender</b>\n\n"
            f"{user}\n"
            f"🧧 Editing messages is not allowed in this group.\n"
            f"⏳ This message will be removed in <b>{delay}s</b>."
        )

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Updates 🚀", url=UPDATES_LINK)
        ]])

        sent = await message.reply_text(
            warning_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        asyncio.create_task(
            delete_later(
                context.bot,
                message.chat.id,
                message.message_id,
                sent,
                delay,
                user,
            )
        )

    except Exception as e:
        print(f"[EDIT DEBUG] Error in on_edit: {e}")

# ======================
# COMMANDS
# ======================
async def setdelay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat = message.chat
    user = message.from_user

    if chat.type == "private":
        await message.reply_text("🚫 This command works only in groups.")
        return

    if not await is_admin(context, chat.id, user.id):
        await message.reply_text("⚠️ Only admins can use this command.")
        return

    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        await message.reply_text(
            "Usage: `/setdelay <seconds>`",
            parse_mode="Markdown"
        )
        return

    delay = int(args[1])
    update_edit_settings(chat.id, delay_seconds=delay)

    await message.reply_text(
        f"⏳ <b>Edit Delay Updated</b>\n\n"
        f"New delay: <b>{delay}</b> seconds\n\n"
        f"Updates: <a href='{UPDATES_LINK}'>Nexora Bots</a>",
        parse_mode="HTML"
    )

async def editdefender_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat = message.chat
    user = message.from_user

    if chat.type == "private":
        await message.reply_text(
            "🚫 *Edit Defender*\n\nThis command works only in groups.",
            parse_mode="Markdown"
        )
        return

    if not await is_admin(context, chat.id, user.id):
        await message.reply_text(
            "⚠️ *Access Denied*\n\nOnly group admins can manage Edit Defender.",
            parse_mode="Markdown"
        )
        return

    # Bot permission check
    try:
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        if not bot_member.can_delete_messages:
            await message.reply_text(
                "❌ *Missing Permission*\n\n"
                "I need:\n• Delete messages\n\n"
                "Please promote me as admin.",
                parse_mode="Markdown"
            )
            return
    except Exception:
        await message.reply_text(
            "❌ I cannot verify my permissions.\nPlease make me admin."
        )
        return

    args = message.text.split()
    current = get_edit_settings(chat.id)

    if len(args) == 1:
        status = "enabled ✅" if current["is_enabled"] else "disabled ❌"
        delay = current["delay_seconds"]
        await message.reply_text(
            f"🛡️ <b>Edit Defender Updated</b>\n\n"
            f"Now {status} for this group.\n\n"
            f"Updates: <a href='{UPDATES_LINK}'>Nexora Bots</a>",
            parse_mode="HTML"
        )
        return

    if args[1].lower() not in ["on", "off"]:
        await message.reply_text("Usage: `/editdefender on|off`", parse_mode="Markdown")
        return

    enabled = args[1].lower() == "on"
    update_edit_settings(chat.id, is_enabled=enabled)
    status = "enabled ✅" if enabled else "disabled ❌"

    await message.reply_text(
        f"🛡️ <b>Edit Defender Updated</b>\n\n"
        f"Now {status} for this group.\n\n"
        f"Updates: <a href='{UPDATES_LINK}'>Nexora Bots</a>",
        parse_mode="HTML"
    )


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

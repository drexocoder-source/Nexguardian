# commands.py
import sqlite3
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode

DB_FILE = "nexora_guardian.db"

# ======================
# DATABASE
# ======================
def init_command_cleaner_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS command_cleaner
        (chat_id INTEGER PRIMARY KEY,
         is_enabled INTEGER DEFAULT 0)
    """)
    conn.commit()
    conn.close()


def get_command_cleaner(chat_id: int) -> bool:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT is_enabled FROM command_cleaner WHERE chat_id = ?", (chat_id,))
    row = c.fetchone()
    conn.close()
    return bool(row[0]) if row else False


def update_command_cleaner(chat_id: int, enabled: bool):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO command_cleaner (chat_id, is_enabled) VALUES (?, ?)",
        (chat_id, int(enabled))
    )
    conn.commit()
    conn.close()


# ======================
# COMMAND
# ======================
async def cleaner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    # Show status
    if len(args) == 1:
        status = "enabled ✅" if get_command_cleaner(chat.id) else "disabled ❌"
        await message.reply_text(f"🧹 Command cleaner is {status}")
        return

    if args[1].lower() in ["on", "off"]:
        enabled = args[1].lower() == "on"

        # If enabling, check delete rights
        if enabled and not can_delete:
            await message.reply_text(
                "❌ I need *Delete Messages* permission to clean commands.\n\n"
                "Please give me:\n"
                "• Delete messages\n\n"
                "Then try again: `/cleaner on`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        update_command_cleaner(chat.id, enabled)
        status = "enabled ✅" if enabled else "disabled ❌"
        await message.reply_text(f"🧹 Command cleaner {status}")


# ======================
# MESSAGE HANDLER
# ======================
async def command_cleaner_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    chat = message.chat
    if chat.type not in ["group", "supergroup"]:
        return

    if not get_command_cleaner(chat.id):
        return

    # Delete commands
    if message.text.startswith("/"):
        try:
            await message.delete()
        except Exception:
            pass


# ======================
# REGISTER
# ======================
def register_command_cleaner(application):
    init_command_cleaner_db()
    application.add_handler(CommandHandler("cleaner", cleaner_command))
    application.add_handler(
        MessageHandler(filters.TEXT & filters.COMMAND, command_cleaner_handler),
        group=1
    )

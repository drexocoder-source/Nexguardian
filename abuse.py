import sqlite3
import re
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

# ==============================
# ABUSIVE WORDS LIST (MULTI-LANGUAGE)
# ==============================
abuse_words = [
    # Strong English abusive words
    "bc", "bitch", "ass", "shit", "fuck", "damn", "crap", "bastard",
    "slut", "whore", "jerk", "dick", "pussy", "cock", "cunt",
    "bollocks", "bugger", "arse", "twat", "prick", "tosser", "wanker",

    # Hindi abusive words (transliterated)
    "chutiya", "bhosadi", "madarchod", "randi", "harami", "bhains", "lund",
    "gandu", "chodu", "bhenchod", "chutiye", "kaminey", "haramzada",
    "lund ka", "bhosdike", "mc", "bhosadi ke", "gaand", "madarchod",
    "bhen ka loda", "gandu ka", "choot ka", "randi ka", "bhonsadi ka",
    "haram ka", "bhosda", "chootiyapa", "lodu ka", "chutiya ka",
    "gandu ki", "kaminey ka"

    # Optional: more strong words can be added later
]

# ==============================
# Compile regex for fast search
# ==============================
# \b ensures exact word matches (avoids partial matches like "bcoz" triggering "bc")
abuse_pattern = re.compile(r'\b(?:' + '|'.join(re.escape(word) for word in abuse_words) + r')\b', re.IGNORECASE)

# -----------------------------
# DATABASE
# -----------------------------
def init_abuse_db():
    """Create table for group abuse settings."""
    conn = sqlite3.connect("nexora_guardian.db")
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS abuse_settings
           (chat_id INTEGER PRIMARY KEY,
            is_enabled INTEGER DEFAULT 0)"""
    )
    conn.commit()
    conn.close()

def get_abuse_settings(chat_id: int):
    conn = sqlite3.connect("nexora_guardian.db")
    c = conn.cursor()
    c.execute("SELECT is_enabled FROM abuse_settings WHERE chat_id = ?", (chat_id,))
    result = c.fetchone()
    conn.close()
    return bool(result[0]) if result else False

def update_abuse_settings(chat_id: int, is_enabled: bool):
    conn = sqlite3.connect("nexora_guardian.db")
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO abuse_settings (chat_id, is_enabled) VALUES (?, ?)",
        (chat_id, int(is_enabled))
    )
    conn.commit()
    conn.close()

# -----------------------------
# COMMAND
# -----------------------------
async def abuse_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enable/disable abusive word deletion (admin only)"""
    message = update.message
    chat_id = message.chat.id
    user = message.from_user

    # check admin
    member = await context.bot.get_chat_member(chat_id, user.id)
    if not (member.status in ["administrator", "creator"]):
        await message.reply_text("⚠️ Only group admins can use this command.")
        return

    args = message.text.split()
    if len(args) == 1:
        status = "enabled ✅" if get_abuse_settings(chat_id) else "disabled ⚠️"
        await message.reply_text(f"Abusive word filter is currently {status}")
        return

    if args[1].lower() in ["on", "off"]:
        enabled = args[1].lower() == "on"
        update_abuse_settings(chat_id, enabled)
        status = "enabled ✅" if enabled else "disabled ⚠️"
        await message.reply_text(f"Abusive word filter {status}")
    else:
        await message.reply_text("Usage: /abuse [on/off]")

from telegram.constants import ParseMode
from telegram.helpers import mention_html

# -----------------------------
# MESSAGE HANDLER
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.helpers import mention_html
from telegram.constants import ParseMode

# -----------------------------
async def abuse_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check every message for abusive words and mention the sender."""
    message = update.message
    if not message or not message.chat or not message.text:
        return

    chat_id = message.chat.id
    if not get_abuse_settings(chat_id):
        return

    text = message.text.lower()
    if abuse_pattern.search(text):
        try:
            await message.delete()

            # Mention the user in the warning message
            user_mention = mention_html(message.from_user.id, message.from_user.first_name)

            warning_text = f"{user_mention} Don’t use prohibited words 🧧"

            # Support button
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("Support 🍀", url="https://t.me/NexoraBots_Support")
            ]])

            await context.bot.send_message(
                chat_id,
                warning_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"[ABUSE] Failed to delete message: {e}")

# -----------------------------
OWNER_ID = 7995262033  # Replace with your ID

# -----------------------------
# Owner-only commands to manage abuse_words list
async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add abusive word (owner only)."""
    user = update.effective_user
    if user.id != OWNER_ID:
        return  # Ignore non-owner

    args = context.args
    if not args:
        await update.message.reply_text("❌ Usage: /add <word>")
        return

    word = args[0].lower()
    if word in abuse_words:
        await update.message.reply_text(f"⚠️ Word '{word}' already exists in the list.")
        return

    abuse_words.append(word)

    # Recompile regex
    global abuse_pattern
    abuse_pattern = re.compile(r'\b(?:' + '|'.join(re.escape(w) for w in abuse_words) + r')\b', re.IGNORECASE)

    await update.message.reply_text(f"✅ Word '{word}' added to abusive list.")

async def rm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove abusive word (owner only)."""
    user = update.effective_user
    if user.id != OWNER_ID:
        return  # Ignore non-owner

    args = context.args
    if not args:
        await update.message.reply_text("❌ Usage: /rm <word>")
        return

    word = args[0].lower()
    if word not in abuse_words:
        await update.message.reply_text(f"⚠️ Word '{word}' not found in the list.")
        return

    abuse_words.remove(word)

    # Recompile regex
    global abuse_pattern
    abuse_pattern = re.compile(r'\b(?:' + '|'.join(re.escape(w) for w in abuse_words) + r')\b', re.IGNORECASE)

    await update.message.reply_text(f"✅ Word '{word}' removed from abusive list.")

# -----------------------------
# Register all handlers in main
def register_abuse_handlers(application):
    init_abuse_db()
    application.add_handler(CommandHandler("abuse", abuse_command))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CommandHandler("rm", rm_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, abuse_message_handler))

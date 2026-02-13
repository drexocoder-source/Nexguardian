import sqlite3
import re
import asyncio
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode
from telegram.helpers import mention_html

# =========================
# CONFIG
# =========================

OWNER_ID = 8294062042
SUPPORT_LINK = "https://t.me/Nexxxxxo_bots"
ABUSE_FILE = "abusewords.txt"

# ==============================
# NORMALIZER
# ==============================

def normalize_text(text: str) -> str:
    text = text.lower()
    replacements = {
        "1": "i", "!": "i",
        "3": "e",
        "4": "a", "@": "a",
        "5": "s", "$": "s",
        "0": "o",
        "*": "", "#": "", "_": "", "-": ""
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(.)\1{2,}", r"\1", text)
    return text

# ==============================
# LOAD WORDS FROM FILE
# ==============================

def load_abuse_words():
    try:
        with open(ABUSE_FILE, "r", encoding="utf-8") as f:
            return [line.strip().lower() for line in f if line.strip()]
    except FileNotFoundError:
        open(ABUSE_FILE, "w").close()
        return []

abuse_words = load_abuse_words()

def rebuild_regex():
    global abuse_pattern
    abuse_pattern = re.compile(
        r'\b(?:' + '|'.join(re.escape(w) for w in abuse_words) + r')\b',
        re.IGNORECASE
    )

rebuild_regex()

# ==============================
# DATABASE
# ==============================

def init_abuse_db():
    conn = sqlite3.connect("nexora_guardian.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS abuse_settings
        (chat_id INTEGER PRIMARY KEY, is_enabled INTEGER DEFAULT 0)
    """)
    conn.commit()
    conn.close()

def get_abuse_settings(chat_id: int):
    conn = sqlite3.connect("nexora_guardian.db")
    c = conn.cursor()
    c.execute("SELECT is_enabled FROM abuse_settings WHERE chat_id=?", (chat_id,))
    r = c.fetchone()
    conn.close()
    return bool(r[0]) if r else False

def update_abuse_settings(chat_id: int, enabled: bool):
    conn = sqlite3.connect("nexora_guardian.db")
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO abuse_settings VALUES (?,?)",
        (chat_id, int(enabled))
    )
    conn.commit()
    conn.close()

# ==============================
# /abuse COMMAND
# ==============================

async def abuse_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat = msg.chat
    user = msg.from_user

    if chat.type == "private":
        await msg.reply_text("❌ Use in groups only.")
        return

    member = await context.bot.get_chat_member(chat.id, user.id)
    if member.status not in ["administrator", "creator"]:
        await msg.reply_text("⚠️ Only admins.")
        return

    bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
    if not bot_member.can_delete_messages:
        await msg.reply_text("❌ Give me Delete Messages permission.")
        return

    args = msg.text.split()

    if len(args) == 1:
        status = "enabled ✅" if get_abuse_settings(chat.id) else "disabled ❌"
        await msg.reply_text(f"Abuse filter is {status}")
        return

    if args[1].lower() in ["on", "off"]:
        enabled = args[1].lower() == "on"
        update_abuse_settings(chat.id, enabled)
        await msg.reply_text(
            f"Abuse filter {'enabled ✅' if enabled else 'disabled ❌'}"
        )

# ==============================
# MESSAGE HANDLER
# ==============================

async def abuse_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    if not get_abuse_settings(msg.chat.id):
        return

    norm = normalize_text(msg.text)
    if abuse_pattern.search(norm):
        try:
            await msg.delete()
            mention = mention_html(msg.from_user.id, msg.from_user.first_name)
            warn = await context.bot.send_message(
                msg.chat.id,
                f"{mention}\nDon’t use prohibited words 🧧",
                parse_mode=ParseMode.HTML
            )
            await asyncio.sleep(3)
            await warn.delete()
        except Exception as e:
            print("[DELETE ERROR]", e)

# ==============================
# OWNER DM ONLY /add
# ==============================

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message

    if user.id != OWNER_ID or msg.chat.type != "private":
        return

    args = context.args
    if not args:
        return

    word = args[0].lower()
    if word in abuse_words:
        await msg.reply_text("Already exists")
        return

    abuse_words.append(word)
    with open(ABUSE_FILE, "a", encoding="utf-8") as f:
        f.write("\n" + word)

    rebuild_regex()
    await msg.reply_text(f"Added: {word}")

# ==============================
# OWNER DM ONLY /rm
# ==============================

async def rm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message

    if user.id != OWNER_ID or msg.chat.type != "private":
        return

    args = context.args
    if not args:
        return

    word = args[0].lower()
    if word not in abuse_words:
        await msg.reply_text("Not found")
        return

    abuse_words.remove(word)

    with open(ABUSE_FILE, "w", encoding="utf-8") as f:
        for w in abuse_words:
            f.write(w + "\n")

    rebuild_regex()
    await msg.reply_text(f"Removed: {word}")

# ==============================
# REGISTER
# ==============================

def register_abuse_handlers(application):
    init_abuse_db()
    application.add_handler(CommandHandler("abuse", abuse_command))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CommandHandler("rm", rm_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, abuse_message_handler)
    )


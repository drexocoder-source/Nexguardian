import sqlite3
import re
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode
from telegram.helpers import mention_html

# =========================
# CONFIG
# =========================

OWNER_ID = 8294062042
NVIDIA_API_KEY = "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"
SUPPORT_LINK = "https://t.me/Nexxxxxo_bots"

# ==============================
# NORMALIZER (fallback system)
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
# FALLBACK ABUSE LIST
# ==============================

abuse_words = [
    "bc","mc","bsdk","bkl","mkc","mf","stfu",
    "bitch","ass","shit","fuck","slut","whore",
    "chutiya","madarchod","bhenchod","lund",
    "gaand","randi","gandu","harami",
]

abuse_pattern = re.compile(
    r'\b(?:' + '|'.join(re.escape(w) for w in abuse_words) + r')\b',
    re.IGNORECASE
)

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
# NVIDIA AI DETECTION
# ==============================

async def ai_detect_abuse(text: str) -> bool:
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "meta/llama-3.1-70b-instruct",
        "messages": [
            {"role": "system", "content": "Reply only YES or NO. Is this message abusive?"},
            {"role": "user", "content": text}
        ],
        "max_tokens": 5,
        "temperature": 0
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                data = await resp.json()
                reply = data["choices"][0]["message"]["content"].lower()
                return "yes" in reply
    except Exception as e:
        print("[AI ERROR]", e)
        return False

# ==============================
# /abuse COMMAND
# ==============================
async def abuse_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat = msg.chat
    user = msg.from_user

    # Block in DM
    if chat.type == "private":
        await msg.reply_text("❌ This command can only be used in groups.")
        return

    # Check user admin
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status not in ["administrator", "creator"]:
            await msg.reply_text("⚠️ Only group admins can use this command.")
            return
    except Exception:
        await msg.reply_text(
            "❌ I can't verify admin status.\n"
            "Please make sure I'm an admin in this group."
        )
        return

    # Check bot permissions
    try:
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        can_delete = bot_member.can_delete_messages
    except Exception:
        await msg.reply_text(
            "❌ I don't have enough permissions.\n"
            "Please promote me as admin with:\n"
            "• Delete messages"
        )
        return

    args = msg.text.split()

    # Show status
    if len(args) == 1:
        status = "enabled ✅" if get_abuse_settings(chat.id) else "disabled ❌"
        await msg.reply_text(f"AI Abuse filter is {status}")
        return

    if args[1].lower() in ["on", "off"]:
        enabled = args[1].lower() == "on"

        # If enabling, check delete rights
        if enabled and not can_delete:
            await msg.reply_text(
                "❌ I need *Delete Messages* permission to work.\n\n"
                "Please give me this permission:\n"
                "• Delete messages\n\n"
                "Then try again: `/abuse on`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        update_abuse_settings(chat.id, enabled)
        await msg.reply_text(
            f"AI Abuse filter {'enabled ✅' if enabled else 'disabled ❌'}"
        )

# ==============================
# MESSAGE HANDLER
# ==============================

async def abuse_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    chat_id = msg.chat.id
    if not get_abuse_settings(chat_id):
        return

    text = msg.text

    ai_flag = await ai_detect_abuse(text)
    norm = normalize_text(text)
    regex_flag = abuse_pattern.search(norm)

    if ai_flag or regex_flag:
        try:
            await msg.delete()

            mention = mention_html(
                msg.from_user.id,
                msg.from_user.first_name
            )

            warn = await context.bot.send_message(
                chat_id,
                f"{mention}\n"
                f"Don’t use prohibited words 🧧",
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
    msg = update.message
    user = update.effective_user

    if user.id != OWNER_ID:
        return

    if msg.chat.type != "private":
        return

    await msg.delete()
    args = context.args
    if not args:
        return

    word = args[0].lower()
    if word in abuse_words:
        return

    abuse_words.append(word)
    global abuse_pattern
    abuse_pattern = re.compile(
        r'\b(?:' + '|'.join(re.escape(w) for w in abuse_words) + r')\b',
        re.IGNORECASE
    )

# ==============================
# OWNER DM ONLY /rm
# ==============================

async def rm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = update.effective_user

    if user.id != OWNER_ID:
        return

    if msg.chat.type != "private":
        return

    await msg.delete()
    args = context.args
    if not args:
        return

    word = args[0].lower()
    if word not in abuse_words:
        return

    abuse_words.remove(word)
    global abuse_pattern
    abuse_pattern = re.compile(
        r'\b(?:' + '|'.join(re.escape(w) for w in abuse_words) + r')\b',
        re.IGNORECASE
    )

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

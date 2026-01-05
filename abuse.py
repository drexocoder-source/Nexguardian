import sqlite3
import re
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
import asyncio


# ==============================
# ABUSIVE WORDS LIST (MULTI-LANGUAGE)
# ==============================

def normalize_text(text: str) -> str:
    text = text.lower()

    # Replace leetspeak
    replacements = {
        "1": "i", "!": "i",
        "3": "e",
        "4": "a", "@": "a",
        "5": "s", "$": "s",
        "0": "o",
        "*": "",
        "#": "",
        "_": "",
        "-": ""
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    # Remove extra spaces between letters
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(.)\1{2,}", r"\1", text)  # aaa -> a

    return text

def calculate_toxicity(text: str) -> int:
    score = 0

    normalized = normalize_text(text)

    # Exact words
    if abuse_pattern.search(normalized):
        score += 3

    # Phrase abuse
    for phrase in abuse_phrases:
        if phrase in normalized:
            score += 3

    # Spaced abuse (b h e n c h o d)
    spaced = normalized.replace(" ", "")
    if abuse_pattern.search(spaced):
        score += 2

    # Repeated characters abuse
    if re.search(r"(chut|gand|lund|madar|bhen)", normalized):
        score += 1

    return score
    
abuse_phrases = [
    # Maa / Baap insults
    "teri maa", "tera baap", "maa chod", "maa chodne",
    "baap se bakchodi", "baap ko mat sikha",
    "maa ke bare me", "baap ka paisa",

    # Aukaat / Threats
    "aukat me reh", "aukat dikha dunga", "apni aukat",
    "gaand me dum", "dum hai to aa",
    "samne aa", "dekh lunga tujhe",

    # Sexual / vulgar phrases
    "bhosda bhar", "gaand marunga", "teri gaand",
    "maa chuda", "gaand chaat", "lund le",
    "choot me", "lund ghusa",

    # Sister abuse
    "behen ke bare me", "behen chod",
    "behen ke sath", "behen ke name pe",

    # Bhojpuri / desi slang
    "tohar maa", "tohar baap",
    "tohar behen", "tohar aukat",
]


abuse_words = [
    # ===== Short forms / common chat abuse =====
    "bc", "mc", "bsdk", "bcc", "bkl", "lkl", "mkc",
    "mf", "wtf", "omfg", "stfu",

    # ===== English abusive words =====
    "bitch", "ass", "shit", "fuck", "damn", "crap", "bastard",
    "slut", "whore", "jerk", "dick", "pussy", "cock", "cunt",
    "bollocks", "bugger", "arse", "twat", "prick", "tosser",
    "wanker", "motherfucker", "retard", "idiot", "moron",

    # ===== Hindi / Hinglish abusive words =====
    "chutiya", "chutiye", "chutiyapa",
    "madarchod", "madarjat", "harami", "haramzada",
    "bhenchod", "behenchod", "bhen ke lode",
    "bhosadi", "bhosdike", "bhonsadi", "bhosda",
    "randi", "randibaaz",
    "lund", "lodu", "lode", "loda",
    "gaand", "gandu", "gandfaad",
    "choot", "chodu", "chut",
    "kaminey", "kutta", "kutti",
    "saala", "saali", "haraami",

    # ===== Combined abusive phrases (single token style) =====
    "lundka", "bhenkaloda", "maachod", "gaandfaad",
    "chootka", "randika", "ganduka",

    # ===== Bhojpuri / desi slang =====
    "tohar", "tohri", "bhosri",
    "gandmara", "lundbaaz",

    # ===== Mild but toxic (optional, can disable later) =====
    "pagal", "bewakoof", "gadhe", "ullu",
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
    message = update.message
    if not message or not message.text:
        return

    chat_id = message.chat.id
    if not get_abuse_settings(chat_id):
        return

    toxicity = calculate_toxicity(message.text)

    if toxicity >= 3:
        try:
            await message.delete()

            user_mention = mention_html(
                message.from_user.id,
                message.from_user.first_name
            )

            warning_text = (
                f"{user_mention}\n"
                f"Don’t use prohibited words 🧧"
            )

            sent = await context.bot.send_message(
                chat_id,
                warning_text,
                parse_mode=ParseMode.HTML
            )

            # Auto delete warning after 3 seconds
            await asyncio.sleep(3)
            await sent.delete()

        except Exception as e:
            print(f"[ABUSE AI] Error: {e}")

# -----------------------------
OWNER_ID = 8294062042  # Replace with your ID

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

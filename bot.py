from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatMemberUpdated
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    ContextTypes,
    filters,
)
import asyncio
import sqlite3
import os
import requests
import time
from datetime import datetime

# custom modules
from edit import setdelay_command, editdefender_command, id_command, on_edit, init_edit_db
from media import init_media_db, media_command, interval_command, media_handler
from abuse import register_abuse_handlers, init_abuse_db
# ======================
# CONFIG
# ======================
BOT_TOKEN = "8472284333:AAELqEsjqJEYJGQtuod0FNmyYkzElvx1m1o"
ADMIN_USER_ID = 7995262033
TELEGRAPH_URL = "https://graph.org/file/855bf51853efeb6c72866-cea0a3a8655dd75ad4.jpg"

# ======================
# DATABASE
# ======================
def init_db():
    conn = sqlite3.connect("nexora_guardian.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  username TEXT,
                  first_name TEXT,
                  timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS groups
                 (chat_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

def save_user(user_id, username, first_name, timestamp):
    conn = sqlite3.connect("nexora_guardian.db")
    c = conn.cursor()
    c.execute("INSERT INTO users (user_id, username, first_name, timestamp) VALUES (?, ?, ?, ?)",
              (user_id, username, first_name, timestamp))
    conn.commit()
    conn.close()

def get_users_count():
    conn = sqlite3.connect("nexora_guardian.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(DISTINCT user_id) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_all_users():
    conn = sqlite3.connect("nexora_guardian.db")
    c = conn.cursor()
    c.execute("SELECT DISTINCT user_id FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def add_group(chat_id: int):
    conn = sqlite3.connect("nexora_guardian.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO groups (chat_id) VALUES (?)", (chat_id,))
    conn.commit()
    conn.close()

def get_all_groups():
    conn = sqlite3.connect("nexora_guardian.db")
    c = conn.cursor()
    c.execute("SELECT chat_id FROM groups")
    groups = [row[0] for row in c.fetchall()]
    conn.close()
    return groups

# ======================
# MESSAGES
# ======================
WELCOME_MSG = """
𝗡𝗲𝘅𝗼𝗿𝗮 𝗚𝘂𝗮𝗿𝗱𝗶𝗮𝗻 』𓆩🛡𓆪
Hey @{username}! Welcome to the Ultimate Telegram Security Enforcer!

⚙️ Key Features:
- Detect & remove edited messages
- Block harmful content
- Admin tools for safety

🛡️ Protect your group with Nexora Guardian! use /help to learn more.

➜ Add Nexora Guardian to your group for ironclad security!
"""
HELP_MSG = """
🛡️ <b>Nexora Guardian Commands</b> 🛡️

⚙️ <b>General Commands:</b>
- <code>/start</code> → Activate the bot
- <code>/stats</code> → View bot statistics
- <code>/id</code> → Show your user & group ID

📢 <b>Admin & Broadcast:</b>
- <code>/logs</code> → Check logs (admin only)
- <code>/broadcast</code> → Forward a message to all users & groups (admin only)

🛡️ <b>Edit Defender:</b>
- <code>/setdelay &lt;seconds&gt;</code> → Set delay for edit defender
- <code>/antiedit on/off</code> → Enable or disable edit defender

🖼️ <b>Media Auto-Delete:</b>
- <code>/media</code> → Manage media auto-delete settings
- <code>/interval</code> → Set media delete interval

⚠️ <b>Abuse & Moderation:</b>
- <code>/abuse</code> → To enable/disable abuse word filter

💬 Stay safe, enforce rules, and keep your groups clean! ✨
"""


# ======================
# HANDLERS
# ======================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    username = user.username or user.first_name

    # Save user info
    save_user(user.id, username, user.first_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # If used in a group, save the group
    if chat.type in ["group", "supergroup"]:
        add_group(chat.id)
        print(f"[START_COMMAND] Saved group: {chat.id}")

    # Prepare keyboard
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Support", url="https://t.me/CLG_fun_zone")],
        [InlineKeyboardButton("Add to Group", url="https://t.me/NexGuardian_Bot?startgroup=new")]
    ])
   # Prepare welcome message
    welcome_text = WELCOME_MSG.format(username=username)

    # Send photo with caption or fallback to text
    try:
        if not os.path.exists("temp_image.jpg"):
            r = requests.get(TELEGRAPH_URL, stream=True, timeout=10)
            with open("temp_image.jpg", "wb") as f:
                for chunk in r.iter_content(128):
                    f.write(chunk)

        await update.message.reply_photo(
            "temp_image.jpg",
            caption=welcome_text,
            reply_markup=keyboard
        )
    except:
        await update.message.reply_text(
            welcome_text,
            reply_markup=keyboard
        )
        
from telegram import InputMediaPhoto

async def send_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sends help message with temp_image.jpg in HTML format.
    Works for both /help command and button callback.
    """
    # Ensure the image exists
    if not os.path.exists("temp_image.jpg"):
        r = requests.get(TELEGRAPH_URL, stream=True, timeout=10)
        with open("temp_image.jpg", "wb") as f:
            for chunk in r.iter_content(128):
                f.write(chunk)

    # If called from a callback query (button)
    if update.callback_query:
        query = update.callback_query
        await query.answer()  # Acknowledge callback

        chat_id = query.message.chat.id
        message_id = query.message.message_id

        try:
            # Edit original message to include image + help text (HTML)
            await context.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=InputMediaPhoto(media="temp_image.jpg", caption=HELP_MSG, parse_mode="HTML")
            )
        except Exception as e:
            print(f"[HELP] Failed to edit message: {e}")
            # fallback: send as new message quoting original
            await context.bot.send_photo(
                chat_id=chat_id,
                photo="temp_image.jpg",
                caption=HELP_MSG,
                parse_mode="HTML",
                reply_to_message_id=message_id
            )
    else:  # Called via /help command
        chat_id = update.effective_chat.id
        msg_id = update.message.message_id

        await context.bot.send_photo(
            chat_id=chat_id,
            photo="temp_image.jpg",
            caption=HELP_MSG,
            parse_mode="HTML",
            reply_to_message_id=msg_id  # quote the command message
        )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import platform
    start_time = time.time()

    user_count = len(get_all_users())
    group_count = len(get_all_groups())
    ping = int((time.time() - start_time) * 1000)
    python_ver = platform.python_version()

    stats_message = (
        "*📊 Nexora Guardian Stats*\n\n"
        f"🧑‍💻 Total Users\\: `{user_count}`\n"
        f"🏘️ Total Groups\\: `{group_count}`\n"
        f"⏱ Ping\\: `{ping} ms`\n"
        f"🐍 Python\\: `{python_ver}`"
    )

    await update.message.reply_text(stats_message, parse_mode="MarkdownV2")

async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    await update.message.reply_text("Logs feature is not active yet. Use /stats instead.")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only bot admin can use
    if update.effective_user.id != ADMIN_USER_ID:
        return

    # Must reply to a message to broadcast
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message to broadcast.")
        return

    replied = update.message.reply_to_message
    user_ids = get_all_users()
    group_ids = get_all_groups()
    targets = user_ids + group_ids

    success, failed = 0, 0
    for target in targets:
        try:
            # Forward the original message
            await context.bot.forward_message(
                chat_id=target,
                from_chat_id=replied.chat_id,
                message_id=replied.message_id
            )
            success += 1
            await asyncio.sleep(0.1)  # small delay to avoid flood
        except Exception as e:
            print(f"[BROADCAST] Failed to forward to {target}: {e}")
            failed += 1

    # Send detailed stats after forwarding
    await update.message.reply_text(
        f"📢 Broadcast finished!\n"
        f" Successfully forwarded: {success}\n"
        f" Failed to forward: {failed}\n"
        f"💬 Total targets: {len(targets)}"
    )

# === GROUP TRACKING ===
# === GROUP TRACKING ===
async def track_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Track when the bot is added to a group.
    Saves the group ID in the database.
    """
    chat_member: ChatMemberUpdated = update.my_chat_member  # For bot updates
    bot = await context.bot.get_me()

    # Check if the bot itself was added
    if chat_member.new_chat_member.user.id == bot.id:
        chat_id = chat_member.chat.id
        add_group(chat_id)  # Save group to DB
        print(f"[TRACK_GROUP] Bot added to group: {chat_id}")

async def handle_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await on_edit(update, context)
# --- Bot added to group welcome ---

# ======================
# MAIN
def main():
    # Initialize DBs
    init_db()
    init_edit_db()
    init_media_db()
    init_abuse_db()  # <--- Abuse DB
    print("Nexora Guardian is running...")

    # Create bot app
    app = Application.builder().token(BOT_TOKEN).build()

    # --- Command Handlers ---
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", send_help))                  # /help command
    app.add_handler(CallbackQueryHandler(send_help, pattern="send_help"))    # Help button callback
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("logs", logs_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("setdelay", setdelay_command))
    app.add_handler(CommandHandler("antiedit", editdefender_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("media", media_command))
    app.add_handler(CommandHandler("interval", interval_command))

    # --- Edited message listener ---
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_message))

    # --- Media auto-delete ---
    media_filters = (
        filters.PHOTO
        | filters.VIDEO
        | filters.Sticker.ALL
    )
    app.add_handler(MessageHandler(media_filters, media_handler))

    # Track bot being added to groups
    app.add_handler(ChatMemberHandler(track_group, ChatMemberHandler.MY_CHAT_MEMBER))

    # --- Abuse handlers ---
    register_abuse_handlers(app)

    # Run polling
    app.run_polling()

if __name__ == "__main__":
    main()

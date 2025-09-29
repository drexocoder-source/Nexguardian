import os
import time
import platform
import requests
import asyncio
import sqlite3
from datetime import datetime
import shutil


from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
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

# === CUSTOM MODULES ===
from edit import setdelay_command, editdefender_command, id_command, on_edit, init_edit_db
from media import init_media_db, media_command, interval_command, media_handler
from abuse import register_abuse_handlers, init_abuse_db


# ======================
# CONFIG
# ======================
BOT_TOKEN = "8472284333:AAELqEsjqJEYJGQtuod0FNmyYkzElvx1m1o"
ADMIN_USER_ID = 7995262033
BANNER_URL = "https://graph.org/file/855bf51853efeb6c72866-cea0a3a8655dd75ad4.jpg"
STATS_IMAGE = "temp_image.jpg"
DB_FILE = "nexora_guardian.db"
OWNER_ID = 7995262033  # Owner ID to send DB backups

# ======================
# DATABASE
# ======================
def init_db():
    conn = sqlite3.connect(DB_FILE)
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
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO users (user_id, username, first_name, timestamp) VALUES (?, ?, ?, ?)",
              (user_id, username, first_name, timestamp))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT DISTINCT user_id FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def get_all_groups():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT chat_id FROM groups")
    groups = [row[0] for row in c.fetchall()]
    conn.close()
    return groups

def add_group(chat_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO groups (chat_id) VALUES (?)", (chat_id,))
    conn.commit()
    conn.close()

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
# IMAGE HELPERS
# ======================
def ensure_image():
    if os.path.exists(STATS_IMAGE):
        return
    try:
        r = requests.get(BANNER_URL, stream=True, timeout=10)
        if r.status_code == 200:
            with open(STATS_IMAGE, "wb") as f:
                for chunk in r.iter_content(128):
                    f.write(chunk)
            print("[IMAGE] Banner downloaded.")
    except Exception as e:
        print(f"[IMAGE] Failed to download banner: {e}")

# ======================
# COMMAND HANDLERS
# ======================
LOG_GROUP_ID = -1002962367553  # Replace with your actual log group ID

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    username = user.username or user.first_name

    # Check if user already exists
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE user_id = ?", (user.id,))
    exists = c.fetchone()  # None if user not in DB
    conn.close()

    # Save user to DB if new
    if not exists:
        save_user(user.id, username, user.first_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # -----------------------------
        # Log new user to log group
        # -----------------------------
        try:
            log_text = f"🎟 New User Joined!\n👤 Name: {username}\n🆔 ID: {user.id}"
            await context.bot.send_message(LOG_GROUP_ID, log_text)
        except Exception as e:
            print(f"[LOG] Failed to send new user log: {e}")

    if chat.type in ["group", "supergroup"]:
        add_group(chat.id)

    # Send welcome message
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Support 🧶", url="https://t.me/NexoraBots_Support"),
            InlineKeyboardButton("Add to Group", url="https://t.me/NexGuardian_Bot?startgroup=new")
        ]
    ])

    ensure_image()
    try:
        await update.message.reply_photo(
            photo=STATS_IMAGE,
            caption=WELCOME_MSG.format(username=username),
            reply_markup=keyboard
        )
    except:
        await update.message.reply_text(
            WELCOME_MSG.format(username=username),
            reply_markup=keyboard
        )


async def send_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_image()
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        chat_id = query.message.chat.id
        message_id = query.message.message_id
        try:
            await context.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=InputMediaPhoto(media=STATS_IMAGE, caption=HELP_MSG, parse_mode="HTML")
            )
        except:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=STATS_IMAGE,
                caption=HELP_MSG,
                parse_mode="HTML",
                reply_to_message_id=message_id
            )
    else:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=STATS_IMAGE,
            caption=HELP_MSG,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_image()
    start = time.time()
    user_count = len(get_all_users())
    group_count = len(get_all_groups())
    module_count = 22
    sudoers = 3
    assistants = 1
    blocked = 0
    ping = int((time.time() - start) * 1000)
    python_ver = platform.python_version()

    stats_text = (
        "𓆩 ♫ 𝐍𝐞𝐱𝐨𝐫𝐚 𝐆𝐮𝐚𝐫𝐝𝐢𝐚𝐧 ♫ 𓆪\n"
        "📊 *Stats & Information*\n\n"
        f"🧩 Modules : `{module_count}`\n"
        f"🛡️ Sudoers : `{sudoers}`\n"
        f"🤖 Assistants : `{assistants}`\n"
        f"🚫 Blocked : `{blocked}`\n"
        f"👥 Users : `{user_count}`\n"
        f"🏠 Groups : `{group_count}`\n"
        f"⏱ Ping : `{ping} ms`\n"
        f"🐍 Python : `{python_ver}`\n\n"
        "⚙️ Auto Leaving Assistant : `False`\n"
        "⏳ Play Duration Limit : `17000 minutes`\n"
    )

    await update.message.reply_photo(
        photo=STATS_IMAGE,
        caption=stats_text,
        parse_mode="Markdown"
    )

async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    await update.message.reply_text("Logs feature is not active yet. Use /stats instead.")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message to broadcast.")
        return

    replied = update.message.reply_to_message
    targets = get_all_users() + get_all_groups()
    success = failed = 0

    for t in targets:
        try:
            await context.bot.forward_message(
                chat_id=t,
                from_chat_id=replied.chat_id,
                message_id=replied.message_id
            )
            success += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[BROADCAST] Failed for {t}: {e}")
            failed += 1

    await update.message.reply_text(
        f"📢 Broadcast finished!\n"
        f"✅ Success: {success}\n"
        f"❌ Failed: {failed}\n"
        f"💬 Total: {len(targets)}"
    )

# ======================
# GROUP TRACKING
# ======================
async def track_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_member: ChatMemberUpdated = update.my_chat_member
    bot = await context.bot.get_me()
    if chat_member.new_chat_member.user.id == bot.id:
        add_group(chat_member.chat.id)
        print(f"[TRACK_GROUP] Bot added to group: {chat_member.chat.id}")

async def handle_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await on_edit(update, context)

DB_FILE = "nexora_guardian.db"
OWNER_ID = 7995262033  # Replace with your ID

async def restore_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only the owner can use this command.")
        return

    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text("📄 Reply to a backup `.db` file to restore it.")
        return

    file = update.message.reply_to_message.document
    if not file.file_name.endswith(".db"):
        await update.message.reply_text("❌ Please send a valid `.db` file.")
        return

    try:
        file_path = await file.get_file()
        backup_path = f"backup_{file.file_name}"
        await file_path.download_to_drive(backup_path)

        # Replace current DB
        shutil.copy(backup_path, DB_FILE)
        await update.message.reply_text(f"✅ Database restored successfully from {file.file_name}!")

    except Exception as e:
        await update.message.reply_text(f"❌ Failed to restore database:\n{e}")

async def backup_db_loop(bot):
    """Backup DB every 20 hours and send to owner automatically."""
    while True:
        try:
            if os.path.exists(DB_FILE):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                backup_filename = f"nexora_guardian_{timestamp}.db"
                shutil.copy(DB_FILE, backup_filename)
                await bot.send_document(
                    chat_id=OWNER_ID,
                    document=open(backup_filename, "rb"),
                    caption=f"📂 Automated DB backup: {backup_filename}"
                )
                print(f"[BACKUP] Sent {backup_filename} to owner.")
            else:
                print("[BACKUP] Main DB file not found!")
        except Exception as e:
            print(f"[BACKUP] Failed to send DB: {e}")

        # 20 hours in seconds
        await asyncio.sleep(20 * 60 * 60)

# ======================
# MAIN
# ======================
def main():
    init_db()
    init_edit_db()
    init_media_db()
    init_abuse_db()

    print("Nexora Guardian is running...")

    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", send_help))
    app.add_handler(CallbackQueryHandler(send_help, pattern="send_help"))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("logs", logs_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("setdelay", setdelay_command))
    app.add_handler(CommandHandler("antiedit", editdefender_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("media", media_command))
    app.add_handler(CommandHandler("interval", interval_command))
    app.add_handler(CommandHandler("restore", restore_command))  # Restore command

    # Edited messages
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_message))

    # Media auto-delete
    media_filters = filters.PHOTO | filters.VIDEO | filters.Sticker.ALL
    app.add_handler(MessageHandler(media_filters, media_handler))

    # Group tracking
    app.add_handler(ChatMemberHandler(track_group, ChatMemberHandler.MY_CHAT_MEMBER))

    # Abuse word filters
    register_abuse_handlers(app)

    # -------------------------
    # Background DB backup task
    # -------------------------
    async def start_backup(app):
        asyncio.create_task(backup_db_loop(app.bot))

    # Schedule backup after bot starts
    app.post_init = start_backup

    # Start polling
    app.run_polling()


if __name__ == "__main__":
    main()

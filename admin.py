# admin.py
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode


# -----------------------------
# DELETE COMMAND
# -----------------------------
async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat = message.chat
    user = message.from_user

    # Block in DM
    if chat.type == "private":
        await message.reply_text("🧩 This command works only in groups.")
        return

    # Check admin
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status not in ["administrator", "creator"]:
            await message.reply_text("⚠️ Only group admins can use this command.")
            return
    except Exception:
        await message.reply_text("❌ I can't verify your admin status.")
        return

    # Check bot permissions
    try:
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        if not bot_member.can_delete_messages:
            await message.reply_text(
                "❌ I need <b>Delete Messages</b> permission to work.",
                parse_mode=ParseMode.HTML
            )
            return
    except Exception:
        await message.reply_text("❌ I need admin rights to work.")
        return

    # Must be reply
    if not message.reply_to_message:
        await message.reply_text(
            "⚠️ Please reply to a message.\n\n"
            "Usage:\n"
            "<code>/del</code>\n"
            "<code>/del reason</code>",
            parse_mode=ParseMode.HTML
        )
        return

    target_msg = message.reply_to_message
    target_user = target_msg.from_user

    if not target_user:
        await message.reply_text("❌ Couldn't find the user.")
        return

    mention = f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"

    # Get reason
    reason = " ".join(context.args) if context.args else None

    # Try deleting target message
    try:
        await target_msg.delete()
    except Exception:
        await message.reply_text("❌ Failed to delete the message.")
        return

    # Try deleting command message
    try:
        await message.delete()
    except:
        pass

    # Send permanent notice
    if reason:
        text = (
            f"🧧 {mention} your message was deleted by an admin.\n"
            f"<b>Reason:</b> {reason}"
        )
    else:
        text = (
            f"🧧 {mention} your message was deleted by an admin."
        )

    await context.bot.send_message(
        chat.id,
        text,
        parse_mode=ParseMode.HTML
    )


# -----------------------------
# AUTO DELETE HELPER
# -----------------------------
async def auto_delete(message, seconds: int):
    import asyncio
    await asyncio.sleep(seconds)
    try:
        await message.delete()
    except:
        pass


# -----------------------------
# REGISTER
# -----------------------------
def register_admin(application):
    application.add_handler(CommandHandler(["del", "delete"], delete_command))

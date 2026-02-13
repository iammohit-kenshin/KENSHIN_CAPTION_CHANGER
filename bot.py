import re
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

TOKEN = os.getenv("BOT_TOKEN")

users = {}

# Extract episode number
def extract_episode(text):
    patterns = [
        r"[Ee]pisode\s*(\d+)",
        r"[Ee]p\s*(\d+)",
        r"\bE(\d+)\b"
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id] = {
        "videos": [],
        "template": None
    }
    await update.message.reply_text(
        "Send multiple videos.\nThen type /done"
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in users:
        return

    video = update.message.video
    caption = update.message.caption or ""
    episode = extract_episode(caption)

    users[user_id]["videos"].append({
        "file_id": video.file_id,
        "episode": episode
    })

    await update.message.reply_text("Saved ✅")

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Now send new caption template.\nUse {Ep} for episode number."
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in users:
        return

    users[user_id]["template"] = update.message.text
    await update.message.reply_text("Processing... ⚡")

    for vid in users[user_id]["videos"]:
        caption = users[user_id]["template"]

        if "{Ep}" in caption:
            caption = caption.replace("{Ep}", vid["episode"])

        await context.bot.send_video(
            chat_id=user_id,
            video=vid["file_id"],
            caption=caption,
            parse_mode="Markdown"
        )

    await update.message.reply_text("Done 🚀")

    users[user_id] = {"videos": [], "template": None}

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Fast Caption Bot Running ⚡")
    app.run_polling()

if __name__ == "__main__":
    main()

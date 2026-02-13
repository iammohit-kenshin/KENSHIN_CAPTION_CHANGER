import re
import os
import asyncio
from telegram import Update, InputMediaVideo
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

TOKEN = os.getenv("BOT_TOKEN")

user_data_store = {}

# Extract Episode Number
def extract_episode(text):
    patterns = [
        r"[Ee]pisode\s*(\d+)",
        r"[Ee]p\s*(\d+)",
        r"[Ee][Pp]-?(\d+)",
        r"\bE(\d+)\b"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me multiple videos first.\nThen send /done when finished."
    )
    user_data_store[update.effective_user.id] = {
        "videos": [],
        "caption_template": None,
        "thumbnail": None,
    }

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    video = update.message.video
    caption = update.message.caption or ""

    if user_id not in user_data_store:
        return

    episode = extract_episode(caption)

    user_data_store[user_id]["videos"].append({
        "file_id": video.file_id,
        "old_caption": caption,
        "episode": episode
    })

    await update.message.reply_text("Video saved ✅")

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Now send new caption template.\nUse {Ep} for episode number."
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_data_store:
        return

    data = user_data_store[user_id]

    if not data["caption_template"]:
        data["caption_template"] = text
        await update.message.reply_text(
            "Now send new thumbnail photo OR type 'no'"
        )
    else:
        pass

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_data_store:
        return

    data = user_data_store[user_id]

    photo = update.message.photo[-1]
    data["thumbnail"] = photo.file_id

    await process_videos(update, context)

async def handle_no_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.lower()

    if text == "no":
        await process_videos(update, context)

async def process_videos(update, context):
    user_id = update.effective_user.id
    data = user_data_store[user_id]

    await update.message.reply_text("Processing videos... ⏳")

    for vid in data["videos"]:
        caption = data["caption_template"]

        if "{Ep}" in caption:
            caption = caption.replace("{Ep}", vid["episode"])

        await context.bot.send_video(
            chat_id=user_id,
            video=vid["file_id"],
            caption=caption,
            parse_mode="Markdown",
            thumb=data["thumbnail"]
        )

    await update.message.reply_text("Done ✅")

    user_data_store[user_id] = {
        "videos": [],
        "caption_template": None,
        "thumbnail": None,
    }

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_no_thumbnail))

    print("Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()

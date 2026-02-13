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
ADMIN_ID = 6728678197

users = {}

# 🔐 Admin Check
def is_admin(user_id):
    return user_id == ADMIN_ID

# 🔥 Episode Extractor
def extract_episode(text):
    if not text:
        return ""

    text = text.replace("\xa0", " ")

    patterns = [
        r"[Ee]pisode\s*[:\-]?\s*(\d+)",
        r"[Ee]p\s*[:\-]?\s*(\d+)",
        r"[\|\-\•\⌬\‣]*\s*[Ee]pisode\s*[:\-]?\s*(\d+)",
        r"\bE(\d+)\b"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).zfill(2)

    return ""

# ✨ Convert Markdown Style → HTML
def convert_to_html(text):
    if not text:
        return ""

    lines = text.split("\n")
    new_lines = []

    for line in lines:
        line = line.rstrip()

        # Blockquote support
        if line.startswith(">"):
            content = line[1:].strip()
            line = f"<blockquote>{content}</blockquote>"

        new_lines.append(line)

    text = "\n".join(new_lines)

    # Bold *text*
    text = re.sub(r"\*(.*?)\*", r"<b>\1</b>", text)

    return text

# 🚀 Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    users[ADMIN_ID] = {
        "videos": [],
        "template": None,
        "thumb": None,
        "waiting_thumb": False
    }

    await update.message.reply_text(
        "Admin Mode Activated 🔥\nSend multiple videos.\nThen type /done"
    )

# 🎥 Save Videos
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    video = update.message.video
    caption = update.message.caption or ""
    episode = extract_episode(caption)

    users[ADMIN_ID]["videos"].append({
        "file_id": video.file_id,
        "episode": episode
    })

    await update.message.reply_text("Video Saved ✅")

# ✅ Done
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text(
        "Send new caption template.\nUse {Ep} for episode number."
    )

# 📝 Handle Text
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    data = users.get(ADMIN_ID)
    if not data:
        return

    if not data["template"]:
        data["template"] = update.message.text
        data["waiting_thumb"] = True
        await update.message.reply_text(
            "Send thumbnail image OR type 'no'"
        )
        return

    if data["waiting_thumb"] and update.message.text.lower() == "no":
        data["waiting_thumb"] = False
        await process_videos(update, context)

# 🖼 Thumbnail
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    data = users.get(ADMIN_ID)
    if not data:
        return

    if data["waiting_thumb"]:
        data["thumb"] = update.message.photo[-1].file_id
        data["waiting_thumb"] = False
        await process_videos(update, context)

# ⚡ Ultra Fast Process
async def process_videos(update, context):
    data = users.get(ADMIN_ID)
    if not data:
        return

    await update.message.reply_text("Processing ⚡")

    for vid in data["videos"]:
        caption = data["template"]

        ep = vid["episode"] if vid["episode"] else "??"
        caption = caption.replace("{Ep}", ep)

        caption = convert_to_html(caption)

        await context.bot.send_video(
            chat_id=ADMIN_ID,
            video=vid["file_id"],
            caption=caption,
            parse_mode="HTML",
            thumbnail=data["thumb"] if data["thumb"] else None
        )

    await update.message.reply_text("Done 🚀")

    users[ADMIN_ID] = {
        "videos": [],
        "template": None,
        "thumb": None,
        "waiting_thumb": False
    }

# 🏁 Main
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("PRO Caption Bot Running ⚡")
    app.run_polling()

if __name__ == "__main__":
    main()

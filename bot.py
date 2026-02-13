import os
import json
import re
import logging
from functools import wraps
from typing import Dict, Any

from telegram import Update
from telegram.constants import ParseMode  # ✅ Yaha se import karo
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)

# -------------------- CONFIGURATION --------------------
YOUR_USER_ID = 6728678197
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATA_FILE = "user_data.json"

COLLECTING_VIDEOS, WAITING_CAPTION, WAITING_THUMBNAIL = range(3)

# -------------------- PERSISTENCE --------------------
def load_data() -> Dict[int, Any]:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data: Dict[int, Any]):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# -------------------- AUTHORISATION --------------------
def restricted(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != YOUR_USER_ID:
            await update.message.reply_text("⛔ Unauthorized.")
            return
        return await func(update, context)
    return wrapped

# -------------------- HELPER FUNCTIONS --------------------
def extract_episode_number(original_caption: str) -> str:
    if not original_caption:
        return ""
    match = re.search(r"[Ee]p(?:isode)?\.?\s*(\d+)", original_caption)
    return match.group(1) if match else ""

def replace_ep_placeholder(new_caption: str, ep_number: str) -> str:
    if not new_caption:
        return ""
    return new_caption.replace("{Ep}", ep_number)

# -------------------- COMMAND HANDLERS --------------------
@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    
    data[user_id] = {
        "state": COLLECTING_VIDEOS,
        "videos": [],
        "current_idx": 0,
        "temp_caption": None,
    }
    save_data(data)
    
    await update.message.reply_text(
        "⚡ *Super Fast Caption Changer*\n\n"
        "Ab main videos ko **download nahi karunga** - seedha caption edit karke bhej dunga!\n"
        "Jitni videos bhejni hain bhejo, phir `/done` karo.",
        parse_mode=ParseMode.MARKDOWN,
    )
    return COLLECTING_VIDEOS

@restricted
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    user_data = data.get(user_id)
    
    if not user_data or user_data.get("state") != COLLECTING_VIDEOS:
        return
    
    video = update.message.video
    if not video:
        return
    
    user_data["videos"].append({
        "file_id": video.file_id,
        "caption": update.message.caption or "",
    })
    save_data(data)
    
    await update.message.reply_text(f"✅ Video {len(user_data['videos'])} stored. (Fast mode)")
    return COLLECTING_VIDEOS

@restricted
async def done_collecting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    user_data = data.get(user_id)
    
    if not user_data or not user_data.get("videos"):
        await update.message.reply_text("❌ No videos found.")
        return ConversationHandler.END
    
    user_data["state"] = WAITING_CAPTION
    user_data["current_idx"] = 0
    save_data(data)
    
    await ask_for_caption(update, context, user_id)
    return WAITING_CAPTION

async def ask_for_caption(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    data = load_data()
    user_data = data[user_id]
    idx = user_data["current_idx"]
    total = len(user_data["videos"])
    
    await context.bot.send_message(
        chat_id=user_id,
        text=f"✏️ *Video {idx+1} of {total}*\n"
             "Naya caption bhejo. Use `{{Ep}}` for episode number.\n"
             "HTML tags allowed: `<b>bold</b>`, `<blockquote>quote</blockquote>`\n"
             "`/skip` - original caption rahega",
        parse_mode=ParseMode.HTML,
    )

@restricted
async def receive_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    user_data = data.get(user_id)
    
    if not user_data or user_data.get("state") != WAITING_CAPTION:
        return
    
    idx = user_data["current_idx"]
    video_info = user_data["videos"][idx]
    
    if update.message.text == "/skip":
        new_caption = video_info["caption"]
    else:
        new_caption = update.message.text
    
    ep_number = extract_episode_number(video_info["caption"])
    new_caption = replace_ep_placeholder(new_caption, ep_number)
    
    user_data["temp_caption"] = new_caption
    user_data["state"] = WAITING_THUMBNAIL
    save_data(data)
    
    await update.message.reply_text(
        f"🖼️ Thumbnail bhejo (photo) ya `no text` likho.",
        parse_mode=ParseMode.MARKDOWN,
    )
    return WAITING_THUMBNAIL

@restricted
async def receive_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    user_data = data.get(user_id)
    
    if not user_data or user_data.get("state") != WAITING_THUMBNAIL:
        return
    
    idx = user_data["current_idx"]
    video_info = user_data["videos"][idx]
    new_caption = user_data["temp_caption"]
    total = len(user_data["videos"])
    
    thumbnail_file_id = None
    if update.message.photo:
        thumbnail_file_id = update.message.photo[-1].file_id
    elif update.message.text and update.message.text.lower() == "no text":
        thumbnail_file_id = None
    else:
        await update.message.reply_text("⚠️ Photo ya `no text` bhejo.")
        return WAITING_THUMBNAIL
    
    try:
        await context.bot.send_video(
            chat_id=user_id,
            video=video_info["file_id"],
            caption=new_caption,
            thumbnail=thumbnail_file_id,
            parse_mode=ParseMode.HTML,
            supports_streaming=True,
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ Error: {e}",
        )
    
    user_data["current_idx"] += 1
    user_data["temp_caption"] = None
    
    if user_data["current_idx"] < total:
        user_data["state"] = WAITING_CAPTION
        save_data(data)
        await ask_for_caption(update, context, user_id)
        return WAITING_CAPTION
    else:
        user_data["state"] = COLLECTING_VIDEOS
        user_data["videos"] = []
        user_data["current_idx"] = 0
        save_data(data)
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ *Sab videos process ho gaye!* ⚡\n/start se naya batch.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

@restricted
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    if user_id in data:
        data[user_id] = {"state": COLLECTING_VIDEOS, "videos": [], "current_idx": 0}
        save_data(data)
    await update.message.reply_text("🚫 Cancelled.")
    return ConversationHandler.END

# -------------------- MAIN --------------------
def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
        level=logging.INFO
    )
    
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN missing! Railway me variable add karo.")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            COLLECTING_VIDEOS: [
                MessageHandler(filters.VIDEO, handle_video),
                CommandHandler("done", done_collecting),
            ],
            WAITING_CAPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_caption),
                CommandHandler("skip", receive_caption),
            ],
            WAITING_THUMBNAIL: [
                MessageHandler(filters.PHOTO, receive_thumbnail),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_thumbnail),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("cancel", cancel))
    
    print("🤖 Bot is running in SUPER FAST mode...")
    app.run_polling()

if __name__ == "__main__":
    main()

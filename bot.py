import os
import re
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", "37407868"))
API_HASH = os.environ.get("API_HASH", "yahan_hash_daalo")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "yahan_bot_token")
OWNER_ID = int(os.environ.get("OWNER_ID", "6728678197"))

app = Client(
    "CaptionBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    parse_mode=enums.ParseMode.HTML
)

user_data = {}

def extract_episode(caption):
    if not caption: return "N/A"
    # Smart search for episode number
    match = re.search(r'(?:Episode|Ep|E)\s*[:\-\s]*(\d+)', caption, re.IGNORECASE)
    if not match:
        match = re.search(r'(\d+)', caption)
    return match.group(1) if match else "N/A"

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if message.from_user.id != OWNER_ID: return
    user_data[message.from_user.id] = {"queue": []}
    await message.reply_text("✅ **Bot Fixed!**\nAb videos bhejiye, error nahi aayega.")

@app.on_message(filters.video & filters.private)
async def collect_videos(client, message: Message):
    if message.from_user.id != OWNER_ID: return
    user_id = message.from_user.id
    if user_id not in user_data: user_data[user_id] = {"queue": []}
    user_data[user_id]["queue"].append(message)
    await message.reply_text(f"📥 Added: `{len(user_data[user_id]['queue'])}`", quote=True)

@app.on_message(filters.command("done") & filters.private)
async def mark_done(client, message):
    user_id = message.from_user.id
    if user_id not in user_data or not user_data[user_id]["queue"]:
        return await message.reply_text("❌ Queue khali hai!")
    user_data[user_id]["state"] = "awaiting_caption"
    await message.reply_text("📝 **Naya HTML Caption bhejo.**")

@app.on_message(filters.text & filters.private)
async def handle_text(client, message):
    user_id = message.from_user.id
    if user_id != OWNER_ID or user_id not in user_data: return
    state = user_data[user_id].get("state")

    if state == "awaiting_caption":
        user_data[user_id]["new_caption"] = message.text
        user_data[user_id]["state"] = "awaiting_thumb"
        await message.reply_text("🖼️ **Thumbnail (Photo) bhejiye** ya `no` likhiye.")
    elif state == "awaiting_thumb" and message.text.lower() == "no":
        user_data[user_id]["thumb_path"] = None
        await final_process(client, message, user_id)

@app.on_message(filters.photo & filters.private)
async def handle_photo(client, message):
    user_id = message.from_user.id
    if user_id == OWNER_ID and user_data.get(user_id, {}).get("state") == "awaiting_thumb":
        # Thumbnail change ke liye photo download karni padegi (sirf 50kb ki file hoti hai)
        path = await message.download()
        user_data[user_id]["thumb_path"] = path
        await final_process(client, message, user_id)

async def final_process(client, message, user_id):
    queue = sorted(user_data[user_id]["queue"], key=lambda x: x.id)
    caption_tpl = user_data[user_id]["new_caption"]
    thumb = user_data[user_id].get("thumb_path")
    
    sts = await message.reply_text("⚡ **Changing Captions & Covers...**")
    
    for vid in queue:
        try:
            ep_no = extract_episode(vid.caption or "")
            final_cap = re.sub(r'\{ep\}', ep_no, caption_tpl, flags=re.IGNORECASE)
            
            # FASTEST METHOD: Send using file_id
            await client.send_video(
                chat_id=user_id,
                video=vid.video.file_id, # No download
                caption=final_cap,
                thumb=thumb, # New Thumb
                duration=vid.video.duration,
                width=vid.video.width,
                height=vid.video.height,
                supports_streaming=True
            )
            await asyncio.sleep(0.5)
        except Exception as e:
            await message.reply_text(f"❌ Error: {e}")

    if thumb and os.path.exists(thumb): os.remove(thumb)
    del user_data[user_id]
    await sts.edit_text("✅ **All Done! No more errors.**")

if __name__ == "__main__":
    app.run()

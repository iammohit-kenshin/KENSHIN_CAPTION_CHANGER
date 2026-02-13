import os
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

# --- CONFIGURATION (Directly from Environment Variables) ---
API_ID = int(os.environ.get("API_ID", "37407868"))
API_HASH = os.environ.get("API_HASH", "yahan_hash_daalo")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "yahan_bot_token")
OWNER_ID = int(os.environ.get("OWNER_ID", "6728678197"))

# Bot Client Initialize
app = Client(
    "CaptionBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Temporary storage for user sessions
user_data = {}

# --- Helper Function: Get Episode Number ---
def get_episode_number(old_caption):
    if not old_caption:
        return None
    # Matches digits like 01, 1, 102 etc.
    match = re.search(r'(\d+)', old_caption)
    return match.group(1) if match else None

# --- Command Handlers ---

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("❌ Access Denied! Only Owner can use me.")
    
    await message.reply_text(
        "👋 **Bhai Welcome!**\n\n"
        "1️⃣ Pehle saari Videos ek saath bhej do.\n"
        "2️⃣ Phir `/done` likh kar send karo.\n"
        "3️⃣ Main naya Caption aur Thumbnail mangunga.\n\n"
        "💡 **Caption Tip:** `{Ep}` likhna mat bhulna agar episode no. chahiye!"
    )

@app.on_message(filters.video & filters.private)
async def collect_videos(client, message: Message):
    if message.from_user.id != OWNER_ID:
        return

    user_id = message.from_user.id
    if user_id not in user_data or user_data[user_id].get("state") != "collecting":
        user_data[user_id] = {"state": "collecting", "queue": []}
    
    user_data[user_id]["queue"].append(message)
    await message.reply_text(f"✅ Added! Total: **{len(user_data[user_id]['queue'])}**", quote=True)

@app.on_message(filters.command("done") & filters.private)
async def mark_done(client, message):
    user_id = message.from_user.id
    if user_id not in user_data or not user_data[user_id]["queue"]:
        return await message.reply_text("❌ Pehle kuch videos to bhejo!")
    
    user_data[user_id]["state"] = "awaiting_caption"
    await message.reply_text("📝 **Ab naya Caption bhejo.**\n(Bold/Quote support hai)")

@app.on_message(filters.text & filters.private)
async def handle_text(client, message):
    user_id = message.from_user.id
    if user_id != OWNER_ID or user_id not in user_data:
        return

    state = user_data[user_id].get("state")

    if state == "awaiting_caption":
        user_data[user_id]["new_caption"] = message.text.markdown # Supports Bold/Quote
        user_data[user_id]["state"] = "awaiting_thumb"
        await message.reply_text("🖼️ **Ab Thumbnail photo bhejo.**\nNahi lagana to `no` likh do.")
    
    elif state == "awaiting_thumb" and message.text.lower() == "no":
        user_data[user_id]["thumb_path"] = None
        await start_processing(client, message, user_id)

@app.on_message(filters.photo & filters.private)
async def handle_photo(client, message):
    user_id = message.from_user.id
    if user_id == OWNER_ID and user_data.get(user_id, {}).get("state") == "awaiting_thumb":
        status = await message.reply_text("⏬ Downloading Thumb...")
        path = await message.download()
        user_data[user_id]["thumb_path"] = path
        await status.delete()
        await start_processing(client, message, user_id)

async def start_processing(client, message, user_id):
    queue = user_data[user_id]["queue"]
    caption_tpl = user_data[user_id]["new_caption"]
    thumb = user_data[user_id].get("thumb_path")
    
    prog = await message.reply_text(f"🚀 Processing {len(queue)} files...")
    
    for vid in queue:
        try:
            ep = get_episode_number(vid.caption or "")
            final_cap = caption_tpl.replace("{Ep}", ep) if (ep and "{Ep}" in caption_tpl) else caption_tpl
            
            await client.send_video(
                chat_id=user_id,
                video=vid.video.file_id,
                caption=final_cap,
                thumb=thumb,
                supports_streaming=True
            )
            await asyncio.sleep(1.5) # Flood protection
        except Exception as e:
            await message.reply_text(f"❌ Error: {e}")

    if thumb and os.path.exists(thumb):
        os.remove(thumb)
    
    user_data.pop(user_id)
    await prog.edit_text("✅ **Batch Complete!** Sab bhej diya hai.")

if __name__ == "__main__":
    app.run()

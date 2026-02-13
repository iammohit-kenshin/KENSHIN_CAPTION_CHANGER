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
    bot_token=BOT_TOKEN
)

user_data = {}

def extract_episode(caption):
    if not caption: return "N/A"
    # Episode nikalne ka sabse tagda regex
    match = re.search(r'(?:Episode|Ep|E)\s*[:\-\s]*(\d+)', caption, re.IGNORECASE)
    if not match:
        match = re.search(r'(\d+)', caption)
    return match.group(1) if match else "N/A"

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if message.from_user.id != OWNER_ID: return
    user_data[message.from_user.id] = {"queue": []}
    await message.reply_text("✅ **Bot Ready!**\nAb videos bhejiye, phir `/done` likh kar apna HTML caption bhejna.")

@app.on_message(filters.video & filters.private)
async def collect_videos(client, message: Message):
    if message.from_user.id != OWNER_ID: return
    user_id = message.from_user.id
    if user_id not in user_data: user_data[user_id] = {"queue": []}
    user_data[user_id]["queue"].append(message)
    await message.reply_text(f"📥 Added to Queue: `{len(user_data[user_id]['queue'])}`", quote=True)

@app.on_message(filters.command("done") & filters.private)
async def mark_done(client, message):
    user_id = message.from_user.id
    if user_id not in user_data or not user_data[user_id]["queue"]:
        return await message.reply_text("❌ Queue khali hai!")
    user_data[user_id]["state"] = "awaiting_caption"
    await message.reply_text("📝 **Ab naya Caption bhejo (HTML Tags ke saath).**\n\nExample:\n<code>&lt;b&gt;&lt;blockquote&gt;SENTENCED TO BE A HERO&lt;/blockquote&gt;&lt;/b&gt;</code>")

@app.on_message(filters.text & filters.private)
async def handle_text(client, message):
    user_id = message.from_user.id
    if user_id != OWNER_ID or user_id not in user_data: return
    state = user_data[user_id].get("state")

    if state == "awaiting_caption":
        # Hum message.text.html use nahi karenge kyunki wo entities ko badal deta hai
        # Hum seedha raw text uthayenge aur Pyrogram ko HTML parse karne ko kahenge
        user_data[user_id]["new_caption"] = message.text
        user_data[user_id]["state"] = "awaiting_thumb"
        await message.reply_text("🖼️ **Ab Thumbnail bhejo** ya `no` likho.")
    
    elif state == "awaiting_thumb" and message.text.lower() == "no":
        user_data[user_id]["thumb_path"] = None
        await final_process(client, message, user_id)

@app.on_message(filters.photo & filters.private)
async def handle_photo(client, message):
    user_id = message.from_user.id
    if user_id == OWNER_ID and user_data.get(user_id, {}).get("state") == "awaiting_thumb":
        path = await message.download()
        user_data[user_id]["thumb_path"] = path
        await final_process(client, message, user_id)

async def final_process(client, message, user_id):
    queue = sorted(user_data[user_id]["queue"], key=lambda x: x.id)
    caption_tpl = user_data[user_id]["new_caption"]
    thumb = user_data[user_id].get("thumb_path")
    
    sts = await message.reply_text("⚡ **Quotes apply ho rahe hain...**")
    
    for vid in queue:
        try:
            ep_no = extract_episode(vid.caption or "")
            # Custom replacement for {ep}
            final_cap = re.sub(r'\{ep\}', ep_no, caption_tpl, flags=re.IGNORECASE)
            
            await client.send_video(
                chat_id=user_id,
                video=vid.video.file_id,
                caption=final_cap,
                thumb=thumb,
                parse_mode=enums.ParseMode.HTML, # 👈 Yahi Quotes enable karega
                duration=vid.video.duration,
                width=vid.video.width,
                height=vid.video.height,
                supports_streaming=True
            )
            await asyncio.sleep(0.6)
        except Exception as e:
            await message.reply_text(f"❌ Formatting Error: {e}\n\nCheck karein ki HTML tags sahi se close hue hain ya nahi.")

    if thumb and os.path.exists(thumb): os.remove(thumb)
    del user_data[user_id]
    await sts.edit_text("✅ **All Done! Quotes aur Bold apply ho gaye.**")

if __name__ == "__main__":
    app.run()

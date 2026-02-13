import os
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config

# Bot Client Initialize
app = Client(
    "CaptionBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# Data Storage (Temporary RAM mein)
# Note: Agar bot restart hoga to queue clear ho jayegi.
user_data = {} 

# --- Helper Functions ---
def get_episode_number(old_caption):
    """Purane caption se pehla number nikalta hai"""
    if not old_caption:
        return None
    match = re.search(r'(\d+)', old_caption)
    return match.group(1) if match else None

# --- Handlers ---

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(
        "👋 **Hello Bhai!**\n\n"
        "Mai ek Batch Caption Changer Bot hu.\n"
        "1. Mujhe videos bhejo (Jitni chaho).\n"
        "2. Jab ho jaye to `/done` type karo.\n"
        "3. Mai naya caption aur thumbnail mangunga.\n"
        "4. Fir magic dekhna! 🚀"
    )

@app.on_message(filters.video & filters.private)
async def collect_videos(client, message: Message):
    user_id = message.from_user.id
    
    # Sirf owner use kar sake (Security)
    if user_id != Config.OWNER_ID:
        return

    if user_id not in user_data:
        user_data[user_id] = {"state": "collecting", "queue": []}
    
    # Agar abhi collection mode on nahi hai to reset karein
    if user_data[user_id].get("state") != "collecting":
         user_data[user_id] = {"state": "collecting", "queue": []}

    # Video add karo
    user_data[user_id]["queue"].append(message)
    await message.reply_text(f"✅ **Added to queue.** Total: {len(user_data[user_id]['queue'])}", quote=True)

@app.on_message(filters.command("done") & filters.private)
async def mark_done(client, message):
    user_id = message.from_user.id
    if user_id not in user_data or not user_data[user_id]["queue"]:
        return await message.reply_text("❌ Pehle kuch videos to bhejo bhai!")
    
    user_data[user_id]["state"] = "awaiting_caption"
    await message.reply_text(
        "📝 **Ab naya Caption bhejo.**\n\n"
        "💡 **Tip:** Agar tumhare caption me `{Ep}` hoga, to mai usse purani video ke episode number se replace kar dunga.\n\n"
        "Example:\n`Naruto Shippuden - Ep {Ep} [720p] @ChannelName`"
    )

@app.on_message(filters.text & filters.private)
async def handle_text(client, message):
    user_id = message.from_user.id
    if user_id not in user_data:
        return

    state = user_data[user_id].get("state")

    # 1. Caption set karna
    if state == "awaiting_caption":
        user_data[user_id]["new_caption"] = message.text.markdown # Bold/Mono support karega
        user_data[user_id]["state"] = "awaiting_thumb"
        await message.reply_text(
            "🖼️ **Ab Thumbnail bhejo.**\n\n"
            "Agar naya thumbnail nahi lagana, to bas `no` likh kar bhej do."
        )
    
    # 2. Thumbnail ko skip karna ("no" text)
    elif state == "awaiting_thumb" and message.text.lower() == "no":
        user_data[user_id]["thumb_path"] = None
        await start_processing(client, message, user_id)

@app.on_message(filters.photo & filters.private)
async def handle_photo(client, message):
    user_id = message.from_user.id
    if user_id in user_data and user_data[user_id].get("state") == "awaiting_thumb":
        status_msg = await message.reply_text("⏬ Downloading thumbnail...")
        path = await message.download()
        user_data[user_id]["thumb_path"] = path
        await status_msg.delete()
        await start_processing(client, message, user_id)

async def start_processing(client, message, user_id):
    queue = user_data[user_id]["queue"]
    new_caption_template = user_data[user_id]["new_caption"]
    thumb_path = user_data[user_id].get("thumb_path")
    
    status_msg = await message.reply_text(f"🚀 **Processing {len(queue)} videos...**")
    
    for vid_msg in queue:
        try:
            # 1. Episode Number Logic
            original_caption = vid_msg.caption or ""
            ep_num = get_episode_number(original_caption)
            
            # Agar {Ep} hai aur number mila, replace karo, nahi to waisa hi rehne do
            final_caption = new_caption_template
            if "{Ep}" in final_caption and ep_num:
                final_caption = final_caption.replace("{Ep}", ep_num)
            
            # 2. Send Video
            # Hum file_id use karenge taaki download/upload na karna pade (fast)
            # Lekin agar thumbnail change karna hai to re-upload jaisa behave karega server side par
            
            await client.send_video(
                chat_id=user_id,
                video=vid_msg.video.file_id,
                caption=final_caption,
                thumb=thumb_path, # Agar None hai to purana/default rahega
                supports_streaming=True
            )
            
            await asyncio.sleep(2) # Floodwait se bachne ke liye
            
        except Exception as e:
            await message.reply_text(f"❌ Error in a file: {e}")

    # Cleanup
    if thumb_path and os.path.exists(thumb_path):
        os.remove(thumb_path)
    
    del user_data[user_id]
    await status_msg.edit_text("✅ **All Done! Process Complete.**")

if __name__ == "__main__":
    print("Bot Started...")
    app.run()

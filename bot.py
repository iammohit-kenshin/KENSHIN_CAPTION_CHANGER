import os
from pyrogram import Client, filters
from pyrogram.types import Message

# ================== CONFIG (Railway Variables) ==================

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

# ================================================================

app = Client(
    "UltraFastThumbBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

user_data = {}

# ================== START COMMAND ==================

@app.on_message(filters.command("start"))
async def start_handler(client, message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.reply("🔥 Ultra Fast Thumbnail Bot Ready!")
    else:
        await message.reply("⛔ Admin Only Bot")

# ================== SAVE VIDEO ==================

@app.on_message(filters.video & filters.user(ADMIN_ID))
async def save_video(client, message: Message):

    user_data[message.from_user.id] = {
        "file_id": message.video.file_id,
        "duration": message.video.duration,
        "width": message.video.width,
        "height": message.video.height,
        "step": None
    }

    await message.reply("✅ Video Saved!\n\nAb /done likho.")

# ================== DONE COMMAND ==================

@app.on_message(filters.command("done") & filters.user(ADMIN_ID))
async def done_handler(client, message: Message):

    if message.from_user.id not in user_data:
        await message.reply("⚠️ Pehle video bhejo.")
        return

    user_data[message.from_user.id]["step"] = "episode"
    await message.reply("📌 Episode number bhejo.")

# ================== MAIN PROCESS SYSTEM ==================

@app.on_message(filters.user(ADMIN_ID))
async def process_steps(client, message: Message):

    user_id = message.from_user.id

    if user_id not in user_data:
        return

    step = user_data[user_id].get("step")

    # ===== EPISODE STEP =====
    if step == "episode":
        user_data[user_id]["episode"] = message.text.strip()
        user_data[user_id]["step"] = "caption"
        await message.reply("📝 HTML Caption bhejo.\n\n{Ep} likhoge to auto replace hoga.")

    # ===== CAPTION STEP =====
    elif step == "caption":
        ep = user_data[user_id]["episode"]
        caption = message.text.replace("{Ep}", ep)

        user_data[user_id]["caption"] = caption
        user_data[user_id]["step"] = "thumb"

        await message.reply("🖼 Thumbnail bhejo ya `no` likho.")

    # ===== THUMB STEP =====
    elif step == "thumb":

        thumb_path = None

        if message.text and message.text.lower() == "no":
            thumb_path = None

        elif message.photo:
            thumb_path = await message.download()

        data = user_data[user_id]

        await client.send_video(
            chat_id=message.chat.id,
            video=data["file_id"],  # ⚡ SAME FILE_ID = ULTRA FAST
            caption=data["caption"],
            parse_mode="html",
            thumb=thumb_path,
            duration=data["duration"],
            width=data["width"],
            height=data["height"]
        )

        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)

        await message.reply("🚀 Done Ultra Fast Successfully!")

        user_data.pop(user_id)

# ================== RUN ==================

print("🔥 Bot Started Successfully!")
app.run()

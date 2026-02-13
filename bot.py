import os
from pyrogram import Client, filters
from pyrogram.types import Message

# ================== ENV CONFIG ==================

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

# ================================================

app = Client(
    "UltraFastThumbBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

user_data = {}

# ================== START ==================

@app.on_message(filters.command("start") & filters.user(ADMIN_ID))
async def start_handler(client, message):
    await message.reply("🔥 Bot Active & Ready!")

# ================== SAVE VIDEO ==================

@app.on_message(filters.video & filters.user(ADMIN_ID))
async def save_video(client, message: Message):

    user_data[message.from_user.id] = {
        "file_id": message.video.file_id,
        "duration": message.video.duration,
        "width": message.video.width,
        "height": message.video.height,
        "step": "waiting_done"
    }

    await message.reply("✅ Video Saved!\n\nAb /done likho.")

# ================== DONE ==================

@app.on_message(filters.command("done") & filters.user(ADMIN_ID))
async def done_handler(client, message):

    if message.from_user.id not in user_data:
        await message.reply("⚠️ Pehle video bhejo.")
        return

    user_data[message.from_user.id]["step"] = "episode"
    await message.reply("📌 Episode number bhejo.")

# ================== TEXT HANDLER ==================

@app.on_message(filters.text & filters.user(ADMIN_ID))
async def text_handler(client, message: Message):

    user_id = message.from_user.id

    if user_id not in user_data:
        return

    step = user_data[user_id].get("step")

    # ---------- EPISODE ----------
    if step == "episode":
        user_data[user_id]["episode"] = message.text.strip()
        user_data[user_id]["step"] = "caption"
        await message.reply("📝 HTML Caption bhejo.\n\n{Ep} likhoge to auto replace hoga.")
        return

    # ---------- CAPTION ----------
    if step == "caption":
        ep = user_data[user_id]["episode"]
        caption = message.text.replace("{Ep}", ep)

        user_data[user_id]["caption"] = caption
        user_data[user_id]["step"] = "thumb"

        await message.reply("🖼 Thumbnail bhejo ya `no` likho.")
        return

    # ---------- NO THUMB ----------
    if step == "thumb":
        if message.text and message.text.strip().lower() in ["no", "n", "skip"]:

            data = user_data[user_id]

            await client.send_video(
                chat_id=message.chat.id,
                video=data["file_id"],  # ⚡ Ultra Fast
                caption=data["caption"],
                parse_mode="html",
                duration=data["duration"],
                width=data["width"],
                height=data["height"]
            )

            await message.reply("🚀 Done Ultra Fast Successfully!")
            user_data.pop(user_id)
        return

# ================== PHOTO HANDLER (THUMBNAIL) ==================

@app.on_message(filters.photo & filters.user(ADMIN_ID))
async def thumb_handler(client, message: Message):

    user_id = message.from_user.id

    if user_id not in user_data:
        return

    if user_data[user_id].get("step") != "thumb":
        return

    thumb_path = await message.download()
    data = user_data[user_id]

    await client.send_video(
        chat_id=message.chat.id,
        video=data["file_id"],
        caption=data["caption"],
        parse_mode="html",
        thumb=thumb_path,
        duration=data["duration"],
        width=data["width"],
        height=data["height"]
    )

    if os.path.exists(thumb_path):
        os.remove(thumb_path)

    await message.reply("🚀 Done Ultra Fast Successfully!")
    user_data.pop(user_id)

# ================== RUN ==================

print("🔥 Bot Started Successfully!")
app.run()

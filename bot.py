import os
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ParseMode

# States for conversation
RECEIVING_VIDEOS, RECEIVING_CAPTION, RECEIVING_THUMBNAIL = range(3)

# Store user data
user_sessions = {}

class UserSession:
    def __init__(self):
        self.videos = []
        self.current_video_index = 0
        self.new_caption = None
        self.new_thumbnail = None

def extract_episode_number(caption):
    """Extract episode number from caption"""
    if not caption:
        return None
    
    # Look for patterns - improved for your format
    patterns = [
        r'[Ee]pisode:?\s*(\d+)',  # Episode: 06 or Episode 06
        r'[Ee]p:?\s*(\d+)',       # Ep: 06 or Ep 06
        r'[Ee](\d+)',             # E06
        r'#(\d+)',                # #06
    ]
    
    for pattern in patterns:
        match = re.search(pattern, caption)
        if match:
            return match.group(1)
    return None

def format_caption(caption, episode_number):
    """Replace {Ep} with actual episode number and format text"""
    if not caption:
        return ""
    
    # Replace {Ep} with episode number
    if episode_number:
        caption = caption.replace("{Ep}", episode_number)
        caption = caption.replace("{ep}", episode_number)
    
    # Handle quote formatting: >>text<< becomes quote
    caption = re.sub(r'>>(.*?)<<', r'<blockquote>\1</blockquote>', caption, flags=re.DOTALL)
    
    # Handle bold formatting: **text** becomes <b>text</b>
    caption = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', caption, flags=re.DOTALL)
    
    return caption

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user_id = update.effective_user.id
    user_sessions[user_id] = UserSession()
    
    await update.message.reply_text(
        "🎬 *Caption Changer Bot* 🎬\n\n"
        "Bhai, videos bhejo ek ke baad ek! 📹\n"
        "Jab sab videos bhej do, toh /done command send karo.\n\n"
        "Example:\n"
        "1. Videos bhejo\n"
        "2. /done type karo\n"
        "3. Caption provide karo\n"
        "4. Thumbnail bhejo (ya 'no' likho)\n"
        "5. Bot tumhe modified videos dega! ✨",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return RECEIVING_VIDEOS

async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive videos from user"""
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession()
    
    session = user_sessions[user_id]
    
    # Check if message has video
    if not update.message.video:
        await update.message.reply_text("❌ Please send a video file!")
        return RECEIVING_VIDEOS
    
    video = update.message.video
    caption = update.message.caption or ""
    
    # Extract episode number from original caption
    episode_number = extract_episode_number(caption)
    
    session.videos.append({
        'file_id': video.file_id,
        'original_caption': caption,
        'episode_number': episode_number,
        'width': video.width,
        'height': video.height,
        'duration': video.duration,
        'thumb': video.thumb.file_id if video.thumb else None
    })
    
    caption_preview = caption[:50] + "..." if len(caption) > 50 else caption
    
    await update.message.reply_text(
        f"✅ Video #{len(session.videos)} received!\n"
        f"📝 Original caption: {caption_preview}\n"
        f"🔢 Episode: {episode_number or 'Not detected'}\n\n"
        "➡️ Aur videos bhejo ya /done command do!"
    )
    
    return RECEIVING_VIDEOS

async def done_receiving(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User finished sending videos"""
    user_id = update.effective_user.id
    
    if user_id not in user_sessions or not user_sessions[user_id].videos:
        await update.message.reply_text(
            "❌ Pehle videos bhejo bhai! 😅\n\n"
            "Use /start to begin again."
        )
        return ConversationHandler.END
    
    session = user_sessions[user_id]
    session.current_video_index = 0
    
    video = session.videos[0]
    caption_preview = video['original_caption'][:100] + "..." if len(video['original_caption']) > 100 else video['original_caption']
    
    await update.message.reply_text(
        f"👍 Total {len(session.videos)} videos received!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 Ab Video #1 ke liye caption bhejo:\n\n"
        f"💡 Tips:\n"
        f"• **text** for bold\n"
        f"• >>text<< for quote\n"
        f"• {{Ep}} will be replaced with episode number\n\n"
        f"📄 Original caption:\n{caption_preview}"
    )
    
    return RECEIVING_CAPTION

async def receive_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive new caption from user"""
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ Session expired. Use /start to begin again.")
        return ConversationHandler.END
    
    session = user_sessions[user_id]
    session.new_caption = update.message.text
    
    await update.message.reply_text(
        f"✅ Caption saved for Video #{session.current_video_index + 1}!\n\n"
        f"🖼️ Ab thumbnail bhejo:\n"
        f"• ✅ New photo bhejo for custom thumbnail\n"
        f"• ❌ 'no' likho to skip thumbnail change"
    )
    
    return RECEIVING_THUMBNAIL

async def receive_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive thumbnail from user"""
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ Session expired. Use /start to begin again.")
        return ConversationHandler.END
    
    session = user_sessions[user_id]
    
    # Check if user sent photo or text 'no'
    if update.message.photo:
        # Get the largest photo
        session.new_thumbnail = update.message.photo[-1].file_id
        await update.message.reply_text("✅ Thumbnail saved! Processing...")
    elif update.message.text and update.message.text.lower() == 'no':
        session.new_thumbnail = None
        await update.message.reply_text("✅ Original thumbnail will be kept! Processing...")
    else:
        await update.message.reply_text(
            "❌ Please send a photo or type 'no'\n"
            "Try again:"
        )
        return RECEIVING_THUMBNAIL
    
    # Process this video
    await process_and_send_video(update, context, user_id, session)
    
    # Move to next video or finish
    session.current_video_index += 1
    
    if session.current_video_index < len(session.videos):
        video = session.videos[session.current_video_index]
        caption_preview = video['original_caption'][:100] + "..." if len(video['original_caption']) > 100 else video['original_caption']
        
        await update.message.reply_text(
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 Video #{session.current_video_index + 1} ke liye caption bhejo:\n\n"
            f"📄 Original caption:\n{caption_preview}"
        )
        return RECEIVING_CAPTION
    else:
        await update.message.reply_text(
            "🎉 Sab videos process ho gaye!\n\n"
            "✨ Aur videos process karne ke liye /start command use karo! 😊"
        )
        del user_sessions[user_id]
        return ConversationHandler.END

async def process_and_send_video(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, session: UserSession):
    """Process and send video with new caption and thumbnail"""
    video_data = session.videos[session.current_video_index]
    episode_number = video_data['episode_number']
    
    # Format caption with episode number and text formatting
    final_caption = format_caption(session.new_caption, episode_number)
    
    # Send video with new caption and thumbnail
    try:
        if session.new_thumbnail:
            await context.bot.send_video(
                chat_id=user_id,
                video=video_data['file_id'],
                caption=final_caption,
                parse_mode=ParseMode.HTML,
                thumbnail=session.new_thumbnail,
                width=video_data['width'],
                height=video_data['height'],
                duration=video_data['duration']
            )
        else:
            await context.bot.send_video(
                chat_id=user_id,
                video=video_data['file_id'],
                caption=final_caption,
                parse_mode=ParseMode.HTML,
                width=video_data['width'],
                height=video_data['height'],
                duration=video_data['duration']
            )
        
        await update.message.reply_text(
            f"✅ Video #{session.current_video_index + 1} sent successfully! 🎬"
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error sending video: {str(e)}\n\n"
            f"Please try again or contact support."
        )
        print(f"Error sending video: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation"""
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    await update.message.reply_text(
        "❌ Process cancelled!\n\n"
        "Use /start to begin again. 😊"
    )
    return ConversationHandler.END

def main():
    """Main function to run the bot"""
    # Get bot token from environment variable
    TOKEN = os.environ.get('BOT_TOKEN')
    
    if not TOKEN:
        print("❌ Error: BOT_TOKEN environment variable not set!")
        print("Set it using: export BOT_TOKEN='your_bot_token_here'")
        return
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Create conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            RECEIVING_VIDEOS: [
                MessageHandler(filters.VIDEO, receive_video),
                CommandHandler('done', done_receiving),
            ],
            RECEIVING_CAPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_caption),
            ],
            RECEIVING_THUMBNAIL: [
                MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), receive_thumbnail),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )
    
    application.add_handler(conv_handler)
    
    # Start bot
    print("🤖 Bot is starting...")
    print("Press Ctrl+C to stop")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

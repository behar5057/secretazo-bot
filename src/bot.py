import os
import asyncio
import logging
from starlette.applications import Starlette
from starlette.responses import Response, PlainTextResponse
from starlette.routing import Route
import uvicorn
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import sqlite3
from datetime import datetime

# التوكن والمتغيرات
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))
# Render بيعطي الرابط ده تلقائياً
RENDER_URL = os.getenv('RENDER_EXTERNAL_URL')
PORT = int(os.getenv('PORT', 8000))

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# رسائل البوت
WELCOME_MESSAGE = """
🎭 Welcome to SecretAzo!

Share your secrets anonymously 🤫

✨ *Your message is posted directly to the channel!*

How it works:
1️⃣ Send your message (text, photo, video)
2️⃣ It's posted anonymously to our channel immediately

Your identity stays secret forever!
"""

# قاعدة بيانات بسيطة
class Database:
    def __init__(self):
        os.makedirs('database', exist_ok=True)
        self.conn = sqlite3.connect('database/bot.db', check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS published_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message_text TEXT,
                message_type TEXT,
                file_id TEXT,
                published_at DATETIME,
                channel_message_id INTEGER
            )
        ''')
        self.conn.commit()
    
    def add_published(self, user_id, text, msg_type, file_id, channel_msg_id):
        cursor = self.conn.execute(
            'INSERT INTO published_messages (user_id, message_text, message_type, file_id, published_at, channel_message_id) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, text, msg_type, file_id, datetime.now(), channel_msg_id)
        )
        self.conn.commit()
        return cursor.lastrowid

db = Database()

# دوال البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_MESSAGE)

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message
    
    msg_type = 'text'
    file_id = None
    content = ""
    
    if message.text:
        content = message.text
        msg_type = 'text'
    elif message.photo:
        content = message.caption or "🖼 Photo"
        msg_type = 'photo'
        file_id = message.photo[-1].file_id
    elif message.video:
        content = message.caption or "🎥 Video"
        msg_type = 'video'
        file_id = message.video.file_id
    else:
        await message.reply_text("❌ This type is not supported. Please send text, photo, or video.")
        return
    
    channel_text = f"🤫 Anonymous Secret\n\n{content}\n\n---\n💫 Share your secret: @SecretAzo_bot"
    
    try:
        channel_id = int(CHANNEL_USERNAME) if CHANNEL_USERNAME.startswith('-100') else CHANNEL_USERNAME
        
        if msg_type == 'text':
            channel_message = await context.bot.send_message(
                chat_id=channel_id,
                text=channel_text
            )
        elif msg_type == 'photo' and file_id:
            channel_message = await context.bot.send_photo(
                chat_id=channel_id,
                photo=file_id,
                caption=channel_text
            )
        elif msg_type == 'video' and file_id:
            channel_message = await context.bot.send_video(
                chat_id=channel_id,
                video=file_id,
                caption=channel_text
            )
        
        if channel_message:
            db.add_published(user_id, content, msg_type, file_id, channel_message.message_id)
        
        await message.reply_text("✅ Your secret has been published to the channel!")
        
    except Exception as e:
        logger.error(f"Error publishing: {e}")
        await message.reply_text("❌ Sorry, there was an error. Please try again later.")

# الإعداد الرئيسي للـ Webhook
async def main():
    # بناء تطبيق telegram
    telegram_app = Application.builder().token(BOT_TOKEN).updater(None).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_user_message))
    
    # تعيين webhook
    webhook_url = f"{RENDER_URL}/telegram"
    await telegram_app.bot.set_webhook(webhook_url, allowed_updates=Update.ALL_TYPES)
    logger.info(f"Webhook set to {webhook_url}")
    
    # إعداد Starlette server
    async def telegram(request):
        update = Update.de_json(await request.json(), telegram_app.bot)
        await telegram_app.update_queue.put(update)
        return Response()
    
    async def health(_):
        return PlainTextResponse("ok")
    
    starlette_app = Starlette(routes=[
        Route("/telegram", telegram, methods=["POST"]),
        Route("/healthcheck", health, methods=["GET"]),
        Route("/", health, methods=["GET"]),  # الصفحة الرئيسية
    ])
    
    # تشغيل السيرفر
    config = uvicorn.Config(app=starlette_app, host="0.0.0.0", port=PORT)
    server = uvicorn.Server(config)
    
    async with telegram_app:
        await telegram_app.start()
        await server.serve()
        await telegram_app.stop()

if __name__ == "__main__":
    asyncio.run(main())

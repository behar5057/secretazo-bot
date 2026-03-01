import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
from datetime import datetime
import sqlite3

# التوكن من المتغيرات البيئية
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')  # يجب أن يكون معرف القناة الصحيح
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0')) # قد لا نحتاجه الآن ولكن يمكن تركه

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

✨ *New: Your message is posted directly to the channel!*

How it works:
1️⃣ Send your message (text, photo, video)
2️⃣ It's posted anonymously to our channel immediately

Your identity stays secret forever!
"""

# قاعدة بيانات بسيطة (اختياري لتتبع المنشورات)
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

# وظيفة مساعدة لتحويل مدخلات القناة
async def get_channel_id(channel_input):
    if str(channel_input).startswith('-100'):
        return int(channel_input)
    else:
        return channel_input

# أوامر المستخدمين
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة البدء"""
    await update.message.reply_text(WELCOME_MESSAGE)

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال رسائل المستخدمين ونشرها مباشرة في القناة"""
    user_id = update.effective_user.id
    message = update.message
    
    # تجهيز المعلومات
    msg_type = 'text'
    file_id = None
    content = ""
    
    # تحديد نوع الرسالة
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
    elif message.voice:
        content = "🎤 Voice message"
        msg_type = 'voice'
        file_id = message.voice.file_id
    else:
        await message.reply_text("❌ This type is not supported. Please send text, photo, or video.")
        return
    
    # نص النشر في القناة
    channel_text = f"🤫 Anonymous Secret\n\n{content}\n\n---\n💫 Share your secret: @SecretAzo_bot"
    
    try:
        # الحصول على ID القناة بالصيغة الصحيحة
        channel_id = await get_channel_id(CHANNEL_USERNAME)
        channel_message = None
        
        # نشر في القناة حسب النوع
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
        elif msg_type == 'voice' and file_id:
            channel_message = await context.bot.send_voice(
                chat_id=channel_id,
                voice=file_id,
                caption=channel_text
            )
        
        # حفظ في قاعدة البيانات (اختياري)
        if channel_message:
            db.add_published(user_id, content, msg_type, file_id, channel_message.message_id)
        
        # إشعار المستخدم بالنجاح
        await message.reply_text("✅ Your secret has been published to the channel!")
        logger.info(f"Published message from user {user_id} to channel {CHANNEL_USERNAME}")
        
    except Exception as e:
        logger.error(f"Error publishing to channel: {e}")
        # إرسال رسالة خطأ للمستخدم
        await message.reply_text(f"❌ Sorry, there was an error publishing your secret. Please try again later.")
        # إرسال تقرير الخطأ للمشرف (اختياري)
        if ADMIN_USER_ID:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_USER_ID,
                    text=f"⚠️ Failed to publish message from user {user_id}.\nError: {str(e)}"
                )
            except:
                pass

# أمر إحصائيات للمشرف
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    
    published_count = db.conn.execute('SELECT COUNT(*) FROM published_messages').fetchone()[0]
    stats_text = f"📊 SecretAzo Statistics\n\n✅ Total published: {published_count}"
    await update.message.reply_text(stats_text)

# تشغيل البوت
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # أوامر المستخدمين
    application.add_handler(CommandHandler("start", start))
    
    # أوامر المشرف
    if ADMIN_USER_ID:
        application.add_handler(CommandHandler("stats", admin_stats))
    
    # معالج الرسائل
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_user_message))
    
    print("🤫 SecretAzo Bot (Direct Post Mode) is starting...")
    print(f"🤖 Bot is running! Posts will go directly to: {CHANNEL_USERNAME}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

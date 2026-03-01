import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import os
from datetime import datetime
import sqlite3

# التوكن من المتغيرات البيئية
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# رسائل البوت
WELCOME_MESSAGE = """
🎭 *Welcome to SecretAzo Bot!*

Share your secrets anonymously 🤫

*How it works:*
1️⃣ Send your message
2️⃣ Admin reviews it
3️⃣ Gets posted anonymously to channel
"""

# قاعدة البيانات
class Database:
    def __init__(self):
        os.makedirs('database', exist_ok=True)
        self.conn = sqlite3.connect('database/bot.db', check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS pending_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message_text TEXT,
                message_type TEXT,
                file_id TEXT,
                caption TEXT,
                timestamp DATETIME
            )
        ''')
        self.conn.commit()
    
    def add_pending(self, user_id, text, msg_type, file_id=None, caption=None):
        cursor = self.conn.execute(
            'INSERT INTO pending_messages (user_id, message_text, message_type, file_id, caption, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, text, msg_type, file_id, caption, datetime.now())
        )
        self.conn.commit()
        return cursor.lastrowid

db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة البدء"""
    await update.message.reply_text(WELCOME_MESSAGE, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال الرسائل"""
    user_id = update.effective_user.id
    message = update.message
    
    # استقبال النص
    if message.text:
        msg_id = db.add_pending(user_id, message.text, 'text')
        await message.reply_text("✅ Your message has been received! It will be reviewed soon.")
        
        # إرسال للمشرف
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=f"📨 New message from user {user_id}:\n\n{message.text}"
        )

def main():
    """تشغيل البوت"""
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # تشغيل البوت
    print("🤖 SecretAzo Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()

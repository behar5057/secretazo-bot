import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import os
from datetime import datetime
import sqlite3
import asyncio

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

# رسائل البوت (للمستخدمين فقط) - بدون Markdown
WELCOME_MESSAGE = """
🎭 Welcome to SecretAzo!

Share your secrets anonymously 🤫

How it works:
1️⃣ Send your message (text, photo, video)
2️⃣ We review it
3️⃣ Gets posted anonymously to our channel

✨ Your identity stays secret forever!
"""

RECEIVED_MESSAGE = """
✅ Your secret has been received!

We'll review it and post it in our channel if approved.
You'll get a notification when it's live.

Thank you for trusting SecretAzo! 🤫
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
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS published_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_id INTEGER,
                published_at DATETIME,
                channel_message_id INTEGER
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
    
    def get_pending(self, msg_id):
        cursor = self.conn.execute('SELECT * FROM pending_messages WHERE id = ?', (msg_id,))
        return cursor.fetchone()
    
    def delete_pending(self, msg_id):
        self.conn.execute('DELETE FROM pending_messages WHERE id = ?', (msg_id,))
        self.conn.commit()
    
    def add_published(self, original_id, channel_msg_id):
        self.conn.execute(
            'INSERT INTO published_messages (original_id, published_at, channel_message_id) VALUES (?, ?, ?)',
            (original_id, datetime.now(), channel_msg_id)
        )
        self.conn.commit()

db = Database()

# ========== أوامر المستخدمين ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة البدء - للمستخدمين فقط"""
    await update.message.reply_text(WELCOME_MESSAGE)

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال رسائل المستخدمين"""
    user_id = update.effective_user.id
    message = update.message
    
    # تجهيز المعلومات
    msg_type = 'text'
    file_id = None
    caption = None
    content = ""
    
    # تحديد نوع الرسالة
    if message.text:
        content = message.text
        msg_type = 'text'
    elif message.photo:
        content = message.caption or "🖼 Photo"
        msg_type = 'photo'
        file_id = message.photo[-1].file_id
        caption = message.caption
    elif message.video:
        content = message.caption or "🎥 Video"
        msg_type = 'video'
        file_id = message.video.file_id
        caption = message.caption
    elif message.voice:
        content = "🎤 Voice message"
        msg_type = 'voice'
        file_id = message.voice.file_id
    else:
        await message.reply_text("❌ This type is not supported. Please send text, photo, or video.")
        return
    
    # حفظ في قاعدة البيانات
    msg_id = db.add_pending(user_id, content, msg_type, file_id, caption)
    
    # إرسال للمشرف (بدون ما يشوف المستخدم)
    await send_to_admin(context, msg_id, user_id, content, msg_type, file_id, caption)
    
    # تأكيد للمستخدم فقط
    await message.reply_text(RECEIVED_MESSAGE)

# ========== وظائف المشرف ==========

async def send_to_admin(context, msg_id, user_id, content, msg_type, file_id, caption):
    """إرسال الرسالة للمشرف فقط"""
    
    # نص الرسالة للمشرف
    admin_text = f"🔐 New Secret to Review 🔐\n\n"
    admin_text += f"🆔 ID: {msg_id}\n"
    admin_text += f"👤 User: {user_id}\n"
    admin_text += f"📝 Content:\n{content}\n"
    
    # أزرار التحكم
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{msg_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{msg_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # إرسال للمشرف
        if msg_type == 'text':
            await context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=admin_text,
                reply_markup=reply_markup
            )
        elif msg_type == 'photo' and file_id:
            await context.bot.send_photo(
                chat_id=ADMIN_USER_ID,
                photo=file_id,
                caption=admin_text,
                reply_markup=reply_markup
            )
        elif msg_type == 'video' and file_id:
            await context.bot.send_video(
                chat_id=ADMIN_USER_ID,
                video=file_id,
                caption=admin_text,
                reply_markup=reply_markup
            )
        elif msg_type == 'voice' and file_id:
            await context.bot.send_voice(
                chat_id=ADMIN_USER_ID,
                voice=file_id,
                caption=admin_text,
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error sending to admin: {e}")

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة قرارات المشرف"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith('approve_'):
        msg_id = int(data.split('_')[1])
        await approve_secret(query, context, msg_id)
    
    elif data.startswith('reject_'):
        msg_id = int(data.split('_')[1])
        await reject_secret(query, msg_id)

async def approve_secret(query, context, msg_id):
    """الموافقة على سر ونشره في القناة"""
    message = db.get_pending(msg_id)
    
    if not message:
        await query.edit_message_text("❌ Secret not found!")
        return
    
    # نص النشر في القناة - بدون Markdown
    channel_text = f"🤫 Anonymous Secret\n\n{message[2]}\n\n---\n💫 Share your secret: @SecretAzo_bot"
    
    try:
        # نشر في القناة
        if message[3] == 'text':
            sent = await context.bot.send_message(
                chat_id=CHANNEL_USERNAME,
                text=channel_text
            )
        elif message[3] == 'photo' and message[4]:
            sent = await context.bot.send_photo(
                chat_id=CHANNEL_USERNAME,
                photo=message[4],
                caption=channel_text
            )
        elif message[3] == 'video' and message[4]:
            sent = await context.bot.send_video(
                chat_id=CHANNEL_USERNAME,
                video=message[4],
                caption=channel_text
            )
        elif message[3] == 'voice' and message[4]:
            sent = await context.bot.send_voice(
                chat_id=CHANNEL_USERNAME,
                voice=message[4],
                caption=channel_text
            )
        else:
            await query.edit_message_text("❌ Cannot publish this type of message.")
            return
        
        # حفظ في قاعدة البيانات
        db.add_published(msg_id, sent.message_id)
        db.delete_pending(msg_id)
        
        # إشعار المشرف فقط
        await query.edit_message_text(f"✅ Secret {msg_id} published to channel!")
        
        # إشعار المستخدم
        try:
            await context.bot.send_message(
                chat_id=message[1],
                text=f"🎉 Your secret has been published!\n\nCheck out our channel: {CHANNEL_USERNAME}"
            )
        except:
            pass
    
    except Exception as e:
        logger.error(f"Error publishing: {e}")
        await query.edit_message_text(f"❌ Failed to publish: {str(e)}")

async def reject_secret(query, msg_id):
    """رفض سر"""
    message = db.get_pending(msg_id)
    
    if message:
        # إشعار المستخدم فقط
        try:
            await query.get_bot().send_message(
                chat_id=message[1],
                text="📝 Your secret wasn't approved as it doesn't follow our community guidelines."
            )
        except:
            pass
        
        # حذف من قاعدة البيانات
        db.delete_pending(msg_id)
    
    await query.edit_message_text(f"❌ Secret {msg_id} rejected")

# ========== أوامر المشرف ==========

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات للمشرف فقط"""
    # التحقق من أن المستخدم هو المشرف
    if update.effective_user.id != ADMIN_USER_ID:
        return
    
    # إحصائيات بسيطة
    pending_count = db.conn.execute('SELECT COUNT(*) FROM pending_messages').fetchone()[0]
    published_count = db.conn.execute('SELECT COUNT(*) FROM published_messages').fetchone()[0]
    
    stats_text = f"📊 SecretAzo Statistics\n\n"
    stats_text += f"⏳ Pending: {pending_count}\n"
    stats_text += f"✅ Published: {published_count}\n"
    
    await update.message.reply_text(stats_text)

# ========== تشغيل البوت ==========

def main():
    """تشغيل البوت"""
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # أوامر المستخدمين
    application.add_handler(CommandHandler("start", start))
    
    # أوامر المشرف
    application.add_handler(CommandHandler("stats", admin_stats))
    
    # معالجات الرسائل
    application.add_handler(CallbackQueryHandler(admin_callback, pattern='^(approve_|reject_)'))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_user_message))
    
    # معلومات التشغيل
    print("🤫 SecretAzo Bot is starting...")
    print(f"🤖 Bot is running!")
    
    # تشغيل البوت
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

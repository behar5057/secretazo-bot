import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')  # Example: @secretazo_channel
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))

# Bot Info
BOT_USERNAME = "SecretAzo"  # اسم البوت
BOT_LINK = "t.me/SecretAzo_bot"  # رابط البوت (غيري الرابط)

# Messages
WELCOME_MESSAGE = f"""
🎭 *Welcome to {BOT_USERNAME}!*

Share your secrets anonymously 🤫

*How it works:*
1️⃣ Send your message (text, photo, video)
2️⃣ Admin reviews it
3️⃣ Gets posted anonymously to our channel
4️⃣ Your identity stays secret forever!

✨ *What's on your mind?*
"""

HELP_MESSAGE = """
📌 *Commands:*
/start - Start the bot
/help - Show this help
/rules - Guidelines
/about - About SecretAzo

🔐 *Privacy First*
• No personal data stored
• All metadata removed
• Anonymous posting guaranteed
"""

RULES_MESSAGE = """
📋 *SecretAzo Guidelines:*

✅ *Allowed:*
• Personal secrets & confessions
• Seeking anonymous advice
• Sharing experiences
• Venting anonymously

❌ *Not Allowed:*
• Hate speech or bullying
• Personal attacks
• Spam or promotions
• Illegal content
• Doxxing or personal info

⚠️ Violations = Permanent ban
"""

ABOUT_MESSAGE = f"""
🤫 *About {BOT_USERNAME}*

A safe space to share your secrets anonymously.
Your identity is completely protected.

📢 Channel: {CHANNEL_USERNAME}
🤖 Bot: {BOT_LINK}

Built with ❤️ for anonymous sharing
"""

import sqlite3
from datetime import datetime
import os

class Database:
    def __init__(self):
        # التأكد من وجود مجلد database
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
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS banned_users (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                banned_at DATETIME
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                stat_key TEXT PRIMARY KEY,
                stat_value INTEGER
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
    
    def get_all_pending(self):
        cursor = self.conn.execute('SELECT * FROM pending_messages ORDER BY timestamp DESC')
        return cursor.fetchall()
    
    def delete_pending(self, msg_id):
        self.conn.execute('DELETE FROM pending_messages WHERE id = ?', (msg_id,))
        self.conn.commit()
    
    def add_published(self, original_id, channel_msg_id):
        self.conn.execute(
            'INSERT INTO published_messages (original_id, published_at, channel_message_id) VALUES (?, ?, ?)',
            (original_id, datetime.now(), channel_msg_id)
        )
        self.conn.commit()
    
    def get_stats(self):
        stats = {}
        stats['pending'] = self.conn.execute('SELECT COUNT(*) FROM pending_messages').fetchone()[0]
        stats['published'] = self.conn.execute('SELECT COUNT(*) FROM published_messages').fetchone()[0]
        stats['banned'] = self.conn.execute('SELECT COUNT(*) FROM banned_users').fetchone()[0]
        return stats
    
    def is_banned(self, user_id):
        cursor = self.conn.execute('SELECT * FROM banned_users WHERE user_id = ?', (user_id,))
        return cursor.fetchone() is not None
    
    def ban_user(self, user_id, reason="Violated guidelines"):
        self.conn.execute(
            'INSERT OR IGNORE INTO banned_users (user_id, reason, banned_at) VALUES (?, ?, ?)',
            (user_id, reason, datetime.now())
        )
        self.conn.commit()
    
    def unban_user(self, user_id):
        self.conn.execute('DELETE FROM banned_users WHERE user_id = ?', (user_id,))
        self.conn.commit()

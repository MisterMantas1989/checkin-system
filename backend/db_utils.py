from flask import g
import sqlite3

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('chat.db')
        g.db.row_factory = sqlite3.Row
    return g.db

def init_messages_table():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            message TEXT,
            timestamp TEXT
        )
    ''')
    db.commit()

def save_message(user, message, timestamp):
    db = get_db()
    db.execute(
        'INSERT INTO messages (user, message, timestamp) VALUES (?, ?, ?)',
        (user, message, timestamp)
    )
    db.commit()

def get_messages():
    db = get_db()
    return db.execute('SELECT * FROM messages ORDER BY timestamp DESC').fetchall()

import sqlite3  # ← Viktigt!


def init_messages_table():
    db = sqlite3.connect("chat.db")
    cur = db.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            message TEXT,
            timestamp TEXT
        )
    """
    )
    db.commit()
    db.close()


def save_message(user, message, timestamp):
    db = sqlite3.connect("chat.db")
    cur = db.cursor()
    cur.execute(
        "INSERT INTO messages (user, message, timestamp) VALUES (?, ?, ?)",
        (user, message, timestamp),
    )
    db.commit()
    db.close()


def get_messages():
    db = sqlite3.connect("chat.db")
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    cur.execute("SELECT * FROM messages ORDER BY timestamp DESC")
    return cur.fetchall()

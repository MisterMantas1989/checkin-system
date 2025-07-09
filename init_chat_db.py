import sqlite3

conn = sqlite3.connect("chat.db")
cursor = conn.cursor()

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS chat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL
)
"""
)

conn.commit()
conn.close()
print("Tabellen 'chat' skapades!")

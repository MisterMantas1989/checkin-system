import os
import sqlite3

db_path = os.path.join(os.path.dirname(__file__), "chat.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Skapa tabell för in- och utcheckningar
cur.execute(
    """
CREATE TABLE IF NOT EXISTS checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    mobil TEXT,
    checkin_time TEXT,
    checkin_address TEXT,
    checkout_time TEXT,
    checkout_address TEXT,
    work_time_minutes INTEGER
)
"""
)

# Skapa tabell för chat-meddelanden
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

conn.commit()
conn.close()
print("Databasen är klar! Både checkins och messages-tabeller skapades.")

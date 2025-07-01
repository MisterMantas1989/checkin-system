import sqlite3
conn = sqlite3.connect("chat.db")  # eller var din databas ligger!
cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        message TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()
conn.close()
print("Tabellen 'messages' skapad!")

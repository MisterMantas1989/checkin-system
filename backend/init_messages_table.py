import sqlite3

# Anslut till SQLite-databasen (skapar filen om den inte finns)
conn = sqlite3.connect("chat.db")  # Ange rätt sökväg om nödvändigt
cur = conn.cursor()

# Skapa tabellen 'messages' om den inte redan finns
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        message TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
"""
)
conn.commit()
conn.close()
print("Tabellen 'messages' skapad!")

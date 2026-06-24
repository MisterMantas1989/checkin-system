import sqlite3
from datetime import datetime

DB_PATH = "chat.db"


def create_table():
    """Skapa tabellen för in/utcheckning."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS checkins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT NOT NULL,
        checkin_time DATETIME,
        checkout_time DATETIME,
        checkin_address TEXT,
        checkout_address TEXT,
        work_time_minutes INTEGER
    )
    """
    )
    conn.commit()
    conn.close()
    print("Tabell 'checkins' skapad!")


def check_in(user, address):
    """Logga en incheckning för given användare och adress."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO checkins (user, checkin_time, checkin_address)
        VALUES (?, ?, ?)
    """,
        (user, now, address),
    )
    conn.commit()
    conn.close()
    print(f"{user} checkade in {now} på adress: {address}")


def check_out(user, address):
    """Logga en utcheckning för given användare och adress."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Hämta senaste checkin utan utcheckning
    c.execute(
        """
        SELECT id, checkin_time FROM checkins
        WHERE user = ? AND checkout_time IS NULL
        ORDER BY checkin_time DESC LIMIT 1
    """,
        (user,),
    )
    row = c.fetchone()
    if row:
        checkin_id, checkin_time = row
        checkin_time_obj = datetime.strptime(checkin_time, "%Y-%m-%d %H:%M:%S")
        checkout_time_obj = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        work_time = int((checkout_time_obj - checkin_time_obj).total_seconds() // 60)
        c.execute(
            """
            UPDATE checkins
            SET checkout_time = ?, checkout_address = ?, work_time_minutes = ?
            WHERE id = ?
        """,
            (now, address, work_time, checkin_id),
        )
        conn.commit()
        print(f"{user} checkade ut {now} på adress: {address} (Jobbat {work_time} min)")
    else:
        print("Ingen aktiv check-in att checka ut från!")
    conn.close()


def total_worked_minutes(user):
    """Summera totalt arbetad tid i minuter för given användare."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT SUM(work_time_minutes) FROM checkins
        WHERE user = ?
    """,
        (user,),
    )
    total = c.fetchone()[0]
    conn.close()
    return total or 0


# Testkörning
if __name__ == "__main__":
    create_table()
    # check_in("Anna", "Sveavägen 1, Stockholm")
    # check_out("Anna", "Kungsgatan 2, Stockholm")
    # print("Totalt jobbat:", total_worked_minutes("Anna"), "minuter")

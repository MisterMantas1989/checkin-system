import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_db():
    return psycopg2.connect(
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"]
    )

if __name__ == "__main__":
    try:
        conn = get_db()
        print("Anslutning OK!")
        conn.close()
    except Exception as e:
        print("Fel vid anslutning:", e)

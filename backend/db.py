import os
import psycopg2
from dotenv import load_dotenv

# 🔄 Läs in .env
load_dotenv()

def get_db():
    try:
        return psycopg2.connect(
            dbname=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", 5432)
        )
    except KeyError as e:
        raise Exception(f"Saknar miljövariabel: {e}")
    except Exception as e:
        raise Exception(f"Fel vid anslutning till databasen: {e}")

if __name__ == "__main__":
    try:
        conn = get_db()
        print("✅ Anslutning OK!")
        conn.close()
    except Exception as e:
        print("❌", e)


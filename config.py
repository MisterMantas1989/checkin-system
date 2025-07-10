import os
from dotenv import load_dotenv
import re

# Ladda .env-filen (lokalt)
load_dotenv()

# Hämta DATABASE_URL
raw_uri = os.getenv("DATABASE_URL")

# Validera att den finns
if not raw_uri:
    raise ValueError("❌ DATABASE_URL not set!")

# 🛠 Render & Supabase fix: ersätt 'postgres://' med 'postgresql://'
SQLALCHEMY_DATABASE_URI = re.sub(r'^postgres://', 'postgresql://', raw_uri)

# SQLAlchemy setting
SQLALCHEMY_TRACK_MODIFICATIONS = False





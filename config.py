import os
from dotenv import load_dotenv
import re

load_dotenv()

raw_uri = os.getenv("DATABASE_URL")

if raw_uri is None:
    raise ValueError("❌ DATABASE_URL not set!")

# Fix: Convert `postgres://` to `postgresql://` (Render/Supabase issue)
SQLALCHEMY_DATABASE_URI = re.sub(r'^postgres://', 'postgresql://', raw_uri)

SQLALCHEMY_TRACK_MODIFICATIONS = False





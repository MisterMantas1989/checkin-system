from flask import Blueprint, request, jsonify
from models import Checkin, Schema, User, db
from api_auth import get_user_from_token
import pandas as pd

api_misc_bp = Blueprint("api_misc", __name__)

XLSX_HISTORY_FILE = "checkin_data.xlsx"
XLSX_SCHEMA_FILE = "schema_data.xlsx"

def clean(value):
    if pd.isna(value) or value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return str(value)

@api_misc_bp.route("/api/history", methods=["GET"])
def api_history():
    user = get_user_from_token(request)
    if not user:
        return jsonify({"error": "Inte autentiserad"}), 401

    namn = user.name
    entries = []

    # 1. Från Excel-fil
    try:
        df = pd.read_excel(XLSX_HISTORY_FILE, engine="openpyxl")
        df = df[df["Namn"].astype(str).str.strip().str.lower() == namn.strip().lower()]
        for _, row in df.iterrows():
            entries.append({
                "Checkin-datum": clean(row.get("Checkin-datum")),
                "Checkin-tid": clean(row.get("Checkin-tid")),
                "Checkin-adress": clean(row.get("Checkin-adress")),
                "Checkout-datum": clean(row.get("Checkout-datum")),
                "Checkout-tid": clean(row.get("Checkout-tid")),
                "Checkout-adress": clean(row.get("Checkout-adress")),
                "Total tid (minuter)": clean(row.get("Total tid (minuter)"))
            })
    except Exception as e:
        print("Excel error (history):", e)

    # 2. Från databasen
    try:
        db_rows = Checkin.query.filter_by(user=namn).order_by(Checkin.id.desc()).all()
        for r in db_rows:
            entries.append({
                "Checkin-datum": clean(r.checkin_time),
                "Checkin-adress": clean(r.checkin_address),
                "Checkout-datum": clean(r.checkout_time),
                "Checkout-adress": clean(r.checkout_address),
                "Total tid (minuter)": clean(r.work_time_minutes)
            })
    except Exception as e:
        print("DB error (history):", e)

    return jsonify({"entries": entries})

@api_misc_bp.route("/api/schema", methods=["GET"])
def api_schema():
    user = get_user_from_token(request)
    if not user:
        return jsonify({"error": "Inte autentiserad"}), 401

    namn = user.name
    records = []

    # 1. Från databasen
    try:
        db_records = Schema.query.filter(Schema.namn.ilike(namn.strip())).all()
        for r in db_records:
            records.append({
                "Datum": clean(r.datum),
                "Starttid": clean(r.starttid),
                "Sluttid": clean(r.sluttid),
                "Adress": clean(r.adress),
                "Kommentar": clean(r.kommentar)
            })
    except Exception as e:
        print("DB error (schema):", e)

    # 2. Från Excel (komplettering)
    try:
        df = pd.read_excel(XLSX_SCHEMA_FILE, engine="openpyxl")
        df = df[df["Namn"].astype(str).str.strip().str.lower() == namn.strip().lower()]
        for _, row in df.iterrows():
            records.append({
                "Datum": clean(row.get("Datum")),
                "Starttid": clean(row.get("Starttid")),
                "Sluttid": clean(row.get("Sluttid")),
                "Adress": clean(row.get("Adress")),
                "Kommentar": clean(row.get("Kommentar"))
            })
    except Exception as e:
        print("Excel error (schema):", e)

    return jsonify({"schema": records})









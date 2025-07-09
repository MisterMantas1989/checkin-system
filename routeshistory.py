import os
import pandas as pd
from flask import Blueprint, redirect, render_template, session, url_for
from backend.models import Checkin, Schema

history_bp = Blueprint("history", __name__)
XLSX_SCHEMA_FILE = "schema_data.xlsx"  # Filnamn för schema
XLSX_HISTORY_FILE = "checkin_data.xlsx"  # Filnamn för historik

# -------- HISTORIK --------
@history_bp.route("/history")
def history():
    namn = session.get("username")
    if not namn:
        return redirect(url_for("auth.login"))

    entries = []

    # 1. Excel-data
    try:
        df = pd.read_excel(XLSX_HISTORY_FILE, engine="openpyxl")
        # Endast filtrering på namn!
        excel_entries = df[df["Namn"].astype(str).str.strip() == namn]
        for row in excel_entries.to_dict(orient="records"):
            row["källa"] = "Excel"
            entries.append(row)
    except Exception as e:
        print("Excel error:", e)

    # 2. PostgreSQL-data
    try:
        db_rows = (
            Checkin.query.filter_by(user=namn)
            .order_by(Checkin.checkin_time.desc())
            .all()
        )
        for row in db_rows:
            entries.append(
                {
                    "checkin_time": row.checkin_time,
                    "checkout_time": row.checkout_time,
                    "checkin_address": row.checkin_address,
                    "checkout_address": row.checkout_address,
                    "work_time_minutes": row.work_time_minutes,
                    "källa": "PostgreSQL",
                }
            )
    except Exception as e:
        print("Database error:", e)

    # 3. Sortera nyast först
    def get_sort_key(e):
        return (
            e.get("checkin_time")
            or f"{e.get('Checkin-datum', '')} {e.get('Checkin-tid', '')}"
        )

    entries.sort(key=get_sort_key, reverse=True)

    return render_template("history.html", entries=entries)


@history_bp.route("/schema")
def schema():
    namn = session.get("username")
    if not namn:
        return redirect(url_for("auth.login"))

    columns = ["Namn", "Datum", "Starttid", "Sluttid", "Adress", "Kommentar"]
    records = []

    # --- Hämta från SQL (PostgreSQL, via SQLAlchemy) ---
    try:
        db_records = Schema.query.filter(
            Schema.namn.ilike(namn.strip())  # Case-insensitive match
        ).all()
        for r in db_records:
            records.append(
                {
                    "Namn": r.namn,
                    "Datum": r.datum,
                    "Starttid": r.starttid,
                    "Sluttid": r.sluttid,
                    "Adress": r.adress,
                    "Kommentar": r.kommentar or "",
                }
            )
    except Exception as e:
        print("DB error:", e)

    # --- Hämta från Excel ---
    excel_path = "schema_data.xlsx"
    if not os.path.isfile(excel_path):
        # Skapa en tom fil om den saknas
        df = pd.DataFrame(columns=columns)
        df.to_excel(excel_path, index=False)

    try:
        df = pd.read_excel(excel_path, engine="openpyxl")
        # Case-insensitive filtrering på Namn
        user_df = df[
            df["Namn"].astype(str).str.strip().str.lower() == namn.strip().lower()
        ]
        for _, row in user_df.iterrows():
            records.append(
                {
                    "Namn": row["Namn"],
                    "Datum": row["Datum"],
                    "Starttid": row["Starttid"],
                    "Sluttid": row["Sluttid"],
                    "Adress": row["Adress"],
                    "Kommentar": row.get("Kommentar", ""),
                }
            )
    except Exception as e:
        print("Excel error:", e)

    # Sortera på datum (valfritt men rekommenderas)
    try:
        records.sort(key=lambda r: r["Datum"])
    except Exception:
        pass

    return render_template("schema.html", records=records, columns=columns)


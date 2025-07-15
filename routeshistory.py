import os
import pandas as pd
from flask import Blueprint, redirect, render_template, session, url_for
from models import Checkin, Schema
from datetime import datetime
import pytz

history_bp = Blueprint("history", __name__)
XLSX_SCHEMA_FILE = "schema_data.xlsx"
XLSX_HISTORY_FILE = "checkin_data.xlsx"

sweden_tz = pytz.timezone("Europe/Stockholm")

@history_bp.route("/history")
def history():
    namn = session.get("username", "").strip()
    if not namn:
        return redirect(url_for("auth.login"))

    entries = []

    # 1. Från Excel
    try:
        df = pd.read_excel(XLSX_HISTORY_FILE, engine="openpyxl")
        excel_entries = df[df["Namn"].astype(str).str.strip() == namn]
        for row in excel_entries.to_dict(orient="records"):
            try:
                checkin_str = f"{row.get('Checkin-datum', '')} {row.get('Checkin-tid', '')}".strip()
                checkout_str = f"{row.get('Checkout-datum', '')} {row.get('Checkout-tid', '')}".strip()

                checkin_dt = datetime.strptime(checkin_str, "%Y-%m-%d %H:%M:%S")
                checkin_dt = sweden_tz.localize(checkin_dt)

                checkout_dt = None
                if checkout_str:
                    checkout_dt = datetime.strptime(checkout_str, "%Y-%m-%d %H:%M:%S")
                    checkout_dt = sweden_tz.localize(checkout_dt)
            except Exception:
                checkin_dt, checkout_dt = None, None

            entries.append({
                "checkin_time": checkin_dt,
                "checkout_time": checkout_dt,
                "checkin_address": row.get("Checkin-adress", ""),
                "checkout_address": row.get("Checkout-adress", ""),
                "work_time_minutes": row.get("Total tid (minuter)", ""),
                "källa": "Excel"
            })
    except Exception as e:
        print("Excel error:", e)

    # 2. Från PostgreSQL
    try:
        db_rows = (
            Checkin.query.filter_by(user=namn)
            .order_by(Checkin.checkin_time.desc())
            .all()
        )
        for row in db_rows:
            entries.append({
                "checkin_time": row.checkin_time.astimezone(sweden_tz) if row.checkin_time else None,
                "checkout_time": row.checkout_time.astimezone(sweden_tz) if row.checkout_time else None,
                "checkin_address": row.checkin_address,
                "checkout_address": row.checkout_address,
                "work_time_minutes": row.work_time_minutes,
                "källa": "PostgreSQL",
            })
    except Exception as e:
        print("Database error:", e)

    # 3. Sortera på checkin_time
    entries = [e for e in entries if e["checkin_time"]]
    entries.sort(key=lambda e: e["checkin_time"], reverse=True)

    return render_template("history.html", entries=entries)


@history_bp.route("/schema")
def schema():
    namn = session.get("username")
    if not namn:
        return redirect(url_for("auth.login"))

    columns = ["Namn", "Datum", "Starttid", "Sluttid", "Adress", "Kommentar"]
    records = []

    try:
        db_records = Schema.query.filter(Schema.namn.ilike(namn.strip())).all()
        for r in db_records:
            records.append({
                "Namn": r.namn,
                "Datum": r.datum,
                "Starttid": r.starttid,
                "Sluttid": r.sluttid,
                "Adress": r.adress,
                "Kommentar": r.kommentar or "",
            })
    except Exception as e:
        print("DB error:", e)

    if not os.path.isfile(XLSX_SCHEMA_FILE):
        pd.DataFrame(columns=columns).to_excel(XLSX_SCHEMA_FILE, index=False)

    try:
        df = pd.read_excel(XLSX_SCHEMA_FILE, engine="openpyxl")
        user_df = df[df["Namn"].astype(str).str.strip().str.lower() == namn.strip().lower()]
        for _, row in user_df.iterrows():
            records.append({
                "Namn": row["Namn"],
                "Datum": row["Datum"],
                "Starttid": row["Starttid"],
                "Sluttid": row["Sluttid"],
                "Adress": row["Adress"],
                "Kommentar": row.get("Kommentar", ""),
            })
    except Exception as e:
        print("Excel error:", e)

    try:
        records.sort(key=lambda r: r["Datum"])
    except:
        pass

    return render_template("schema.html", records=records, columns=columns)



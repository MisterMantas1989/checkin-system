import os
from datetime import datetime
import pytz
import pandas as pd
from flask import Blueprint, redirect, render_template, request, session, url_for
from geopy.geocoders import Nominatim
from models import Checkin, db
from openpyxl import load_workbook

checkin_bp = Blueprint("checkin", __name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XLSX_FILE = os.path.join(BASE_DIR, "checkin_data.xlsx")

COLUMNS = [
    "Namn", "Checkin-datum", "Checkin-tid", "Checkin-adress",
    "Checkout-datum", "Checkout-tid", "Checkout-adress",
    "Total tid (minuter)", "Total arbetad tid idag"
]

def get_street_address(lat, lon):
    try:
        geolocator = Nominatim(user_agent="checkin_system")
        location = geolocator.reverse((lat, lon), language="sv")
        if location:
            addr = location.raw.get("address", {})
            return f"{addr.get('road', '')} {addr.get('house_number', '')}, {addr.get('city') or addr.get('town') or addr.get('village', '')}".strip(", ")
    except Exception as e:
        print("Adressuppslag fel:", e)
    return "GPS-fel"

def autosize_columns():
    try:
        wb = load_workbook(XLSX_FILE)
        ws = wb.active
        for col in ws.columns:
            max_length = max((len(str(cell.value)) for cell in col if cell.value), default=0)
            ws.column_dimensions[col[0].column_letter].width = max_length + 2
        wb.save(XLSX_FILE)
    except Exception as e:
        print("Fel vid autosize av Excel-kolumner:", e)

def ensure_excel_file():
    if not os.path.exists(XLSX_FILE):
        try:
            df = pd.DataFrame(columns=COLUMNS)
            df.to_excel(XLSX_FILE, index=False, engine="openpyxl")
            autosize_columns()
        except Exception as e:
            print("Fel vid skapande av Excel-fil:", e)

def read_excel_df():
    ensure_excel_file()
    try:
        return pd.read_excel(XLSX_FILE, engine="openpyxl")
    except Exception:
        try:
            df = pd.DataFrame(columns=COLUMNS)
            df.to_excel(XLSX_FILE, index=False, engine="openpyxl")
            return df
        except Exception as e:
            raise RuntimeError("Kan inte återskapa Excel-fil!") from e

def is_user_checked_in(namn):
    namn_lower = namn.strip().lower()

    # Excel
    df = read_excel_df()
    df["Namn_lower"] = df["Namn"].astype(str).str.strip().str.lower()
    excel_mask = df["Namn_lower"] == namn_lower
    checkout_vals = df.loc[excel_mask, "Checkout-datum"].astype(str).str.strip()
    excel_checked_in = (checkout_vals == "").any()

    # PostgreSQL
    db_checked_in = (
        Checkin.query
        .filter(Checkin.user.ilike(namn))
        .filter(Checkin.checkout_time == None)
        .first() is not None
    )
    return excel_checked_in or db_checked_in

@checkin_bp.route("/checkin", methods=["GET", "POST"])
def checkin():
    namn = session.get("username", "").strip()
    if not namn:
        return redirect(url_for("auth.login"))

    if is_user_checked_in(namn):
        return render_template("done.html", message=f"{namn}, du är redan incheckad!", show_checkout=True)

    if request.method == "POST":
        try:
            lat, lon = float(request.form["lat"]), float(request.form["lon"])
        except ValueError:
            return render_template("done.html", message="Ogiltiga GPS-koordinater!")

        now = datetime.now(pytz.timezone("Europe/Stockholm"))
        address = get_street_address(lat, lon)

        # Excel
        new_row = {
            "Namn": namn,
            "Checkin-datum": now.strftime("%Y-%m-%d"),
            "Checkin-tid": now.strftime("%H:%M:%S"),
            "Checkin-adress": address,
            "Checkout-datum": "",
            "Checkout-tid": "",
            "Checkout-adress": "",
            "Total tid (minuter)": "",
            "Total arbetad tid idag": "",
        }
        df = read_excel_df()
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        try:
            df.to_excel(XLSX_FILE, index=False, engine="openpyxl")
            autosize_columns()
        except Exception as e:
            print("Fel vid Excel-skrivning:", e)

        # PostgreSQL — use datetime object (important!)
        try:
            checkin_entry = Checkin(
                user=namn,
                checkin_time=now,  # ✅ use datetime
                checkin_address=address,
            )
            db.session.add(checkin_entry)
            db.session.commit()
            session["checkin_id"] = checkin_entry.id
        except Exception as e:
            print("Fel vid databas-skrivning:", e)
            db.session.rollback()

        return render_template("done.html", message=f"Incheckning registrerad för {namn}", show_checkout=True)

    return render_template("checkin.html", namn=namn)

@checkin_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    namn = session.get("username", "").strip()
    namn_lower = namn.lower()
    if not namn:
        return redirect(url_for("auth.login"))

    df = read_excel_df()
    df["Namn_lower"] = df["Namn"].astype(str).str.strip().str.lower()
    mask = (df["Namn_lower"] == namn_lower)
    checkout_vals = df.loc[mask, "Checkout-datum"].astype(str).str.strip()
    active_mask = mask & (checkout_vals == "")

    if not active_mask.any():
        return render_template("done.html", message="Ingen aktiv incheckning att checka ut från!")

    if request.method == "POST":
        try:
            lat, lon = float(request.form["lat"]), float(request.form["lon"])
        except Exception:
            return render_template("done.html", message="Ogiltiga GPS-koordinater!")

        now = datetime.now(pytz.timezone("Europe/Stockholm"))
        address = get_street_address(lat, lon)
        idx = df[active_mask].index[-1]

        try:
            in_str = f"{df.loc[idx, 'Checkin-datum']} {df.loc[idx, 'Checkin-tid']}"
            in_dt = pytz.timezone("Europe/Stockholm").localize(datetime.strptime(in_str, "%Y-%m-%d %H:%M:%S"))
        except Exception:
            return render_template("done.html", message="Datumformatfel vid incheckning!")

        total_minutes = int((now - in_dt).total_seconds() // 60)
        df.loc[idx, "Checkout-datum"] = now.strftime("%Y-%m-%d")
        df.loc[idx, "Checkout-tid"] = now.strftime("%H:%M:%S")
        df.loc[idx, "Checkout-adress"] = address
        df.loc[idx, "Total tid (minuter)"] = total_minutes

        today_mask = (df["Namn_lower"] == namn_lower) & (df["Checkin-datum"] == now.strftime("%Y-%m-%d"))
        total_today = df.loc[today_mask, "Total tid (minuter)"].fillna(0).astype(float).sum()
        df.loc[today_mask, "Total arbetad tid idag"] = int(total_today)

        df.drop(columns=["Namn_lower"], errors="ignore", inplace=True)
        try:
            df.to_excel(XLSX_FILE, index=False, engine="openpyxl")
            autosize_columns()
        except Exception as e:
            print("Fel vid Excel-skrivning:", e)

        # PostgreSQL – use checkin_id if available
        try:
            checkin_entry = None
            checkin_id = session.get("checkin_id")
            if checkin_id:
                checkin_entry = Checkin.query.get(checkin_id)

            if not checkin_entry:
                checkin_entry = (
                    Checkin.query
                    .filter(Checkin.user.ilike(namn))
                    .filter(Checkin.checkout_time == None)
                    .order_by(Checkin.checkin_time.desc())
                    .first()
                )

            if not checkin_entry:
                print(f"[FEL] Ingen öppen incheckning hittades för {namn}")
                return render_template("done.html", message="Ingen incheckning hittades i databasen.")

            checkin_entry.checkout_time = now
            checkin_entry.checkout_address = address
            checkin_entry.work_time_minutes = total_minutes
            checkin_entry.total_work_today = int(total_today)
            db.session.commit()

        except Exception as e:
            print("Fel vid databas-skrivning:", e)
            db.session.rollback()

        return render_template("done.html", message=f"Utcheckning registrerad för {namn}")

    return render_template("checkout.html")




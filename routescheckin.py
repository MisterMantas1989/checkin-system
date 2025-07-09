import os
from datetime import datetime

import pandas as pd
from flask import Blueprint, redirect, render_template, request, session, url_for
from geopy.geocoders import Nominatim
from backend.models import Checkin, User, db
from openpyxl import load_workbook

checkin_bp = Blueprint("checkin", __name__)
BASE_DIR = os.path.dirname(__file__)
XLSX_FILE = os.path.join(BASE_DIR, "checkin_data.xlsx")

def get_street_address(lat, lon):
    try:
        geolocator = Nominatim(user_agent="checkin_system")
        location = geolocator.reverse((lat, lon), language="sv")
        if location:
            addr = location.raw.get("address", {})
            return f"{addr.get('road', '')} {addr.get('house_number', '')}, {addr.get('city') or addr.get('town') or addr.get('village', '')}".strip(", ")
    except:
        pass
    return "GPS-fel"

def autosize_columns():
    wb = load_workbook(XLSX_FILE)
    ws = wb.active
    for col in ws.columns:
        max_length = max((len(str(cell.value)) for cell in col if cell.value), default=0)
        ws.column_dimensions[col[0].column_letter].width = max_length + 2
    wb.save(XLSX_FILE)

def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)

@checkin_bp.route("/checkin", methods=["GET", "POST"])
def checkin():
    user = get_current_user()
    if not user:
        return redirect(url_for("auth.login"))

    namn = user.name
    mobil = getattr(user, "mobil", "")  # används bara för Excel

    try:
        df = pd.read_excel(XLSX_FILE, engine="openpyxl")
    except:
        df = pd.DataFrame(columns=[
            "Namn", "Mobil", "Checkin-datum", "Checkin-tid", "Checkin-adress",
            "Checkout-datum", "Checkout-tid", "Checkout-adress",
            "Total tid (minuter)", "Total arbetad tid idag"
        ])

    df["Mobil"] = df["Mobil"].astype(str).str.zfill(10)
    mask = (
        (df["Namn"].str.strip() == namn)
        & (df["Mobil"] == mobil)
        & (df["Checkout-datum"].isna() | (df["Checkout-datum"] == ""))
    )

    if mask.any():
        return render_template(
            "done.html", message=f"{namn}, du är redan incheckad!", show_checkout=True
        )

    if request.method == "POST":
        try:
            lat, lon = float(request.form["lat"]), float(request.form["lon"])
        except ValueError:
            return render_template("done.html", message="Ogiltiga GPS-koordinater!")

        now = datetime.now()
        address = get_street_address(lat, lon)

        new_row = {
            "Namn": namn,
            "Mobil": mobil,
            "Checkin-datum": now.strftime("%Y-%m-%d"),
            "Checkin-tid": now.strftime("%H:%M:%S"),
            "Checkin-adress": address,
            "Checkout-datum": "",
            "Checkout-tid": "",
            "Checkout-adress": "",
            "Total tid (minuter)": "",
            "Total arbetad tid idag": "",
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_excel(XLSX_FILE, index=False, engine="openpyxl")
        autosize_columns()

        # ✅ Uppdaterad utan mobil
        db.session.add(
            Checkin(
                user=namn,
                checkin_time=now,
                checkin_address=address,
            )
        )
        db.session.commit()

        return render_template(
            "done.html",
            message=f"Incheckning registrerad för {namn}",
            show_checkout=True,
        )

    return render_template("checkin.html", namn=namn, mobil=mobil)

@checkin_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    user = get_current_user()
    if not user:
        return redirect(url_for("auth.login"))

    namn = user.name

    try:
        df = pd.read_excel(XLSX_FILE, engine="openpyxl")
    except:
        return render_template("done.html", message="Ingen historik hittad")

    mask = (
        (df["Namn"].str.strip() == namn)
        & (df["Checkout-datum"].isna() | (df["Checkout-datum"] == ""))
    )

    if not mask.any():
        return render_template("done.html", message="Ingen aktiv incheckning att checka ut från!")

    if request.method == "POST":
        try:
            lat, lon = float(request.form["lat"]), float(request.form["lon"])
        except ValueError:
            return render_template("done.html", message="Ogiltiga GPS-koordinater!")

        now = datetime.now()
        address = get_street_address(lat, lon)
        idx = df[mask].index[-1]

        try:
            in_str = f"{df.loc[idx, 'Checkin-datum']} {df.loc[idx, 'Checkin-tid']}"
            in_dt = datetime.strptime(in_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return render_template("done.html", message="Datumformatfel vid incheckning!")

        total_minutes = int((now - in_dt).total_seconds() // 60)

        df.loc[idx, "Checkout-datum"] = now.strftime("%Y-%m-%d")
        df.loc[idx, "Checkout-tid"] = now.strftime("%H:%M:%S")
        df.loc[idx, "Checkout-adress"] = address
        df.loc[idx, "Total tid (minuter)"] = total_minutes

        today_mask = (
            (df["Namn"].str.strip() == namn)
            & (df["Checkin-datum"] == now.strftime("%Y-%m-%d"))
        )
        total_today = (
            df.loc[today_mask, "Total tid (minuter)"].fillna(0).astype(float).sum()
        )
        df.loc[today_mask, "Total arbetad tid idag"] = int(total_today)

        df.to_excel(XLSX_FILE, index=False, engine="openpyxl")
        autosize_columns()

        checkin_entry = (
            Checkin.query.filter_by(user=namn, checkout_time=None)
            .order_by(Checkin.checkin_time.desc())
            .first()
        )
        if checkin_entry:
            checkin_entry.checkout_time = now
            checkin_entry.checkout_address = address
            checkin_entry.work_time_minutes = total_minutes
            db.session.commit()

        return render_template(
            "done.html", message=f"Utcheckning registrerad för {namn}"
        )

    return render_template("checkout.html")


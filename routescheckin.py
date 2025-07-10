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
        print("Autosize för kolumner klar")
    except Exception as e:
        print("Fel vid autosize av Excel-kolumner:", e)

def ensure_excel_file():
    print(f"Excel-filens sökväg: {XLSX_FILE}")
    if not os.path.exists(XLSX_FILE):
        print("Excel-fil saknas, skapar ny...")
        try:
            df = pd.DataFrame(columns=COLUMNS)
            df.to_excel(XLSX_FILE, index=False, engine="openpyxl")
            print("Ny Excel-fil skapad.")
            autosize_columns()
        except Exception as e:
            print("Fel vid skapande av Excel-fil:", e)

def read_excel_df():
    ensure_excel_file()
    try:
        df = pd.read_excel(XLSX_FILE, engine="openpyxl")
        print("Excel-fil laddad, rader:", len(df))
        return df
    except Exception as e:
        print("Fel vid läsning av Excel-fil:", e)
        # Återställ filen om den är korrupt
        try:
            print("Försöker återskapa Excel-fil...")
            df = pd.DataFrame(columns=COLUMNS)
            df.to_excel(XLSX_FILE, index=False, engine="openpyxl")
            print("Excel-fil återskapad.")
            return df
        except Exception as e2:
            print("Kritiskt fel: Kan inte återskapa Excel-fil!", e2)
            raise

@checkin_bp.route("/checkin", methods=["GET", "POST"])
def checkin():
    namn = session.get("username", "").strip()
    namn_lower = namn.lower()
    if not namn:
        return redirect(url_for("auth.login"))

    print("\n--- INCHECKNING INITIERAD ---")
    df = read_excel_df()

    df["Namn_lower"] = df["Namn"].astype(str).str.strip().str.lower()
    mask = (df["Namn_lower"] == namn_lower) & (df["Checkout-datum"].isna() | (df["Checkout-datum"] == ""))

    if mask.any():
        print("Användaren är redan incheckad.")
        return render_template("done.html", message=f"{namn}, du är redan incheckad!", show_checkout=True)

    if request.method == "POST":
        try:
            lat, lon = float(request.form["lat"]), float(request.form["lon"])
        except ValueError:
            print("Ogiltiga GPS-koordinater!")
            return render_template("done.html", message="Ogiltiga GPS-koordinater!")

        now = datetime.now(pytz.timezone("Europe/Stockholm"))
        address = get_street_address(lat, lon)

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

        df = df.drop(columns=["Namn_lower"], errors="ignore")
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        try:
            df.to_excel(XLSX_FILE, index=False, engine="openpyxl")
            print("Incheckning skriven till Excel.")
            autosize_columns()
        except Exception as e:
            print("Fel vid skrivning till Excel vid incheckning:", e)

        # Spara till PostgreSQL
        try:
            db.session.add(
                Checkin(
                    user=namn,
                    checkin_time=now.strftime("%Y-%m-%d %H:%M:%S"),
                    checkin_address=address,
                )
            )
            db.session.commit()
            print("Incheckning sparad i databasen.")
        except Exception as e:
            print("Fel vid databas-skrivning:", e)
            db.session.rollback()

        return render_template(
            "done.html",
            message=f"Incheckning registrerad för {namn}",
            show_checkout=True,
        )

    return render_template("checkin.html", namn=namn)

@checkin_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    namn = session.get("username", "").strip()
    namn_lower = namn.lower()
    if not namn:
        return redirect(url_for("auth.login"))

    print("\n--- UTCHECKNING INITIERAD ---")
    df = read_excel_df()

    df["Namn_lower"] = df["Namn"].astype(str).str.strip().str.lower()
    mask = (df["Namn_lower"] == namn_lower) & (df["Checkout-datum"].isna() | (df["Checkout-datum"] == ""))

    if not mask.any():
        print("Ingen aktiv incheckning att checka ut från.")
        return render_template("done.html", message="Ingen aktiv incheckning att checka ut från!")

    if request.method == "POST":
        try:
            lat, lon = float(request.form["lat"]), float(request.form["lon"])
        except ValueError:
            print("Ogiltiga GPS-koordinater!")
            return render_template("done.html", message="Ogiltiga GPS-koordinater!")

        now = datetime.now(pytz.timezone("Europe/Stockholm"))
        address = get_street_address(lat, lon)
        idx = df[mask].index[-1]

        try:
            in_str = f"{df.loc[idx, 'Checkin-datum']} {df.loc[idx, 'Checkin-tid']}"
            in_dt = datetime.strptime(in_str, "%Y-%m-%d %H:%M:%S")
            in_dt = pytz.timezone("Europe/Stockholm").localize(in_dt)
        except Exception as e:
            print("Datumformatfel vid incheckning!", e)
            return render_template("done.html", message="Datumformatfel vid incheckning!")

        total_minutes = int((now - in_dt).total_seconds() // 60)

        df.loc[idx, "Checkout-datum"] = now.strftime("%Y-%m-%d")
        df.loc[idx, "Checkout-tid"] = now.strftime("%H:%M:%S")
        df.loc[idx, "Checkout-adress"] = address
        df.loc[idx, "Total tid (minuter)"] = total_minutes

        today_mask = (
            (df["Namn_lower"] == namn_lower) &
            (df["Checkin-datum"] == now.strftime("%Y-%m-%d"))
        )
        total_today = (
            df.loc[today_mask, "Total tid (minuter)"].fillna(0).astype(float).sum()
        )
        df.loc[today_mask, "Total arbetad tid idag"] = int(total_today)

        df = df.drop(columns=["Namn_lower"], errors="ignore")
        try:
            df.to_excel(XLSX_FILE, index=False, engine="openpyxl")
            print("Utcheckning skriven till Excel.")
            autosize_columns()
        except Exception as e:
            print("Fel vid skrivning till Excel vid utcheckning:", e)

        # Spara till PostgreSQL
        try:
            checkin_entry = (
                Checkin.query.filter_by(user=namn, checkout_time=None)
                .order_by(Checkin.checkin_time.desc())
                .first()
            )
            if checkin_entry:
                checkin_entry.checkout_time = now.strftime("%Y-%m-%d %H:%M:%S")
                checkin_entry.checkout_address = address
                checkin_entry.work_time_minutes = total_minutes
                db.session.commit()
                print("Utcheckning sparad i databasen.")
            else:
                print("Ingen motsvarande incheckning hittad i databasen.")
        except Exception as e:
            print("Fel vid databas-skrivning:", e)
            db.session.rollback()

        return render_template(
            "done.html", message=f"Utcheckning registrerad för {namn}"
        )

    return render_template("checkout.html")


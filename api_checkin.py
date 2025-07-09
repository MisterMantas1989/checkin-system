from flask import Blueprint, request, jsonify
from datetime import datetime
from models import Checkin, User, db
from geopy.geocoders import Nominatim
import pandas as pd
import os
from openpyxl import load_workbook
from api_auth import get_user_from_token

api_checkin_bp = Blueprint("api_checkin", __name__)
XLSX_FILE = "checkin_data.xlsx"

def get_address(lat, lon):
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

@api_checkin_bp.route("/api/status", methods=["GET"])
def api_status():
    user = get_user_from_token(request)
    if not user:
        return jsonify({"error": "Inte autentiserad"}), 401

    df = pd.read_excel(XLSX_FILE, engine="openpyxl")
    namn = user.name

    mask = (
        (df["Namn"].astype(str).str.strip() == namn)
        & (df["Checkout-datum"].isna() | (df["Checkout-datum"] == ""))
    )

    if mask.any():
        row = df[mask].iloc[-1]
        return jsonify({
            "status": "in",
            "checkin_time": f"{row['Checkin-datum']} {row['Checkin-tid']}",
            "checkin_address": row.get("Checkin-adress", ""),
            "lat": None,
            "lon": None
        })
    else:
        return jsonify({"status": "out"})

@api_checkin_bp.route("/api/checkin", methods=["POST"])
def api_checkin():
    user = get_user_from_token(request)
    if not user:
        return jsonify({"error": "Inte autentiserad"}), 401

    data = request.get_json()
    lat = data.get("lat")
    lon = data.get("lon")

    try:
        lat = float(lat)
        lon = float(lon)
    except:
        return jsonify({"error": "Ogiltiga koordinater"}), 400

    namn = user.name
    df = pd.read_excel(XLSX_FILE, engine="openpyxl")

    mask = (
        (df["Namn"].astype(str).str.strip() == namn)
        & (df["Checkout-datum"].isna() | (df["Checkout-datum"] == ""))
    )
    if mask.any():
        return jsonify({"error": "Redan incheckad"}), 400

    now = datetime.now()
    address = get_address(lat, lon)

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

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_excel(XLSX_FILE, index=False, engine="openpyxl")
    autosize_columns()

    db.session.add(
        Checkin(
            user=namn,
            checkin_time=now.strftime("%Y-%m-%d %H:%M:%S"),
            checkin_address=address,
        )
    )
    db.session.commit()

    return jsonify({
        "message": "Incheckning OK",
        "checkin_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "checkin_address": address,
        "lat": lat,
        "lon": lon,
    })

@api_checkin_bp.route("/api/checkout", methods=["POST"])
def api_checkout():
    user = get_user_from_token(request)
    if not user:
        return jsonify({"error": "Inte autentiserad"}), 401

    data = request.get_json()
    lat = data.get("lat")
    lon = data.get("lon")

    try:
        lat = float(lat)
        lon = float(lon)
    except:
        return jsonify({"error": "Ogiltiga koordinater"}), 400

    namn = user.name
    now = datetime.now()
    df = pd.read_excel(XLSX_FILE, engine="openpyxl")
    mask = (
        (df["Namn"].astype(str).str.strip() == namn)
        & (df["Checkout-datum"].isna() | (df["Checkout-datum"] == ""))
    )
    if not mask.any():
        return jsonify({"error": "Ingen aktiv incheckning"}), 400

    idx = df[mask].index[-1]
    in_str = f"{df.loc[idx, 'Checkin-datum']} {df.loc[idx, 'Checkin-tid']}"
    in_dt = datetime.strptime(in_str, "%Y-%m-%d %H:%M:%S")
    total_minutes = int((now - in_dt).total_seconds() // 60)
    address = get_address(lat, lon)

    df.loc[idx, "Checkout-datum"] = now.strftime("%Y-%m-%d")
    df.loc[idx, "Checkout-tid"] = now.strftime("%H:%M:%S")
    df.loc[idx, "Checkout-adress"] = address
    df.loc[idx, "Total tid (minuter)"] = total_minutes

    today_mask = (
        (df["Namn"].astype(str).str.strip() == namn)
        & (df["Checkin-datum"] == now.strftime("%Y-%m-%d"))
    )
    total_today = (
        df.loc[today_mask, "Total tid (minuter)"].fillna(0).astype(int).sum()
    )
    df.loc[today_mask, "Total arbetad tid idag"] = total_today

    df.to_excel(XLSX_FILE, index=False, engine="openpyxl")
    autosize_columns()

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

    return jsonify({
        "message": "Utcheckning OK",
        "checkout_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "checkout_address": address,
        "total_minutes": total_minutes,
        "lat": lat,
        "lon": lon,
    })




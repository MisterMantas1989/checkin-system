from io import BytesIO
import pandas as pd
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.security import generate_password_hash
from models import Checkin, Schema, User, db
import requests

admin_bp = Blueprint("admin", __name__)
ADMIN_PASSWORD = "19890108"  # Byt detta!

def send_push_to_all_users(title, body):
    users = User.query.filter(User.push_token.isnot(None)).all()
    for user in users:
        try:
            requests.post("https://exp.host/--/api/v2/push/send", json={
                "to": user.push_token,
                "sound": "default",
                "title": title,
                "body": body
            })
        except Exception as e:
            print(f"❌ Push-fel till {user.name}: {e}")

@admin_bp.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("losenord", "")
        if password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            session["username"] = "Admin"
            return redirect(url_for("admin.admin_panel"))
        flash("Fel lösenord.")
    return render_template("admin_login.html")

@admin_bp.route("/admin-logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin.admin_login"))

@admin_bp.route("/admin_panel")
def admin_panel():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))
    return render_template("admin_panel.html")

@admin_bp.route("/admin/users", methods=["GET", "POST"])
def admin_users():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    error = None

    if request.method == "POST":
        name = request.form.get("name")
        password = request.form.get("password")

        if not name or not password:
            error = "Alla fält krävs."
        elif User.query.filter_by(name=name).first():
            error = "Användarnamn finns redan."
        else:
            password_hash = generate_password_hash(password)
            new_user = User(name=name, password_hash=password_hash)
            db.session.add(new_user)
            db.session.commit()
            flash("Ny användare skapad.")

    users = User.query.order_by(User.id.desc()).all()
    return render_template("admin_users.html", users=users, error=error)

@admin_bp.route("/admin/users/delete/<int:user_id>", methods=["POST"])
def admin_user_delete(user_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash("Användare raderad.")
    return redirect(url_for("admin.admin_users"))

@admin_bp.route("/admin/logg")
def admin_logg():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    # Hämta användarfilter från query string (från dropboxen)
    selected_user = request.args.get("user", "")

    # Hämta alla användarnamn till dropdown
    alla_anvandare = [row[0] for row in db.session.query(Checkin.username).distinct().all()]

    # Filtrera historik beroende på om admin valt en specifik användare eller "Alla"
    if selected_user:
        entries = Checkin.query.filter_by(username=selected_user).order_by(Checkin.checkin_time.desc()).all()
    else:
        entries = Checkin.query.order_by(Checkin.checkin_time.desc()).all()

    records = [e.to_dict() for e in entries if e is not None]

    # Säkrare kolumngenerering – undvik crash om inga records finns!
    if records:
        columns = list(records[0].keys())
    else:
        columns = []

    return render_template(
        "admin_logg.html",
        records=records,
        columns=columns,
        alla_anvandare=alla_anvandare,
        selected_user=selected_user
    )



@admin_bp.route("/admin/history")
def admin_history():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    user_filter = request.args.get("user", None)
    q = Checkin.query
    if user_filter:
        q = q.filter_by(user=user_filter)
    checkins = q.order_by(Checkin.checkin_time.desc()).all()

    alla_anvandare = [r.user for r in db.session.query(Checkin.user).distinct()]
    return render_template(
        "admin_history.html",
        entries=checkins,
        alla_anvandare=alla_anvandare,
        selected_user=user_filter,
    )

@admin_bp.route("/admin/edit/<int:id>", methods=["GET", "POST"])
def admin_edit(id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    entry = Checkin.query.get(id)
    if not entry:
        flash("Post ej hittad.")
        return redirect(url_for("admin.admin_history"))

    if request.method == "POST":
        entry.checkin_time = request.form["checkin_time"]
        entry.checkout_time = request.form["checkout_time"]
        entry.checkin_address = request.form["checkin_address"]
        entry.checkout_address = request.form["checkout_address"]
        try:
            entry.work_time_minutes = int(request.form["work_time_minutes"])
        except:
            entry.work_time_minutes = None
        db.session.commit()
        flash("Post uppdaterad.")
        return redirect(url_for("admin.admin_history"))

    return render_template("admin_edit.html", entry=entry)

@admin_bp.route("/admin/delete/<int:id>", methods=["POST"])
def admin_delete(id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))
    entry = Checkin.query.get(id)
    if entry:
        db.session.delete(entry)
        db.session.commit()
        flash("Post raderad.")
    return redirect(url_for("admin.admin_history"))

@admin_bp.route("/admin/schema")
def admin_schema():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    user_filter = request.args.get("user", None)
    q = Schema.query
    if user_filter:
        q = q.filter_by(namn=user_filter)
    records = q.order_by(Schema.datum.desc()).all()

    # Hämta alla distinkta användarnamn till dropdown
    alla_anvandare = [r.namn for r in db.session.query(Schema.namn).distinct()]
    columns = ["id", "namn", "datum", "starttid", "sluttid", "adress", "kommentar"]
    record_dicts = [
        {
            "id": r.id,
            "namn": r.namn,
            "datum": r.datum,
            "starttid": r.starttid,
            "sluttid": r.sluttid,
            "adress": r.adress,
            "kommentar": r.kommentar,
        }
        for r in records
    ]
    return render_template(
        "admin_schema.html",
        records=record_dicts,
        columns=columns,
        alla_anvandare=alla_anvandare,
        selected_user=user_filter,
    )

@admin_bp.route("/admin/schema/add", methods=["GET", "POST"])
def admin_schema_add():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    if request.method == "POST":
        namn = request.form["namn"]
        datum = request.form["datum"]
        starttid = request.form["starttid"]
        sluttid = request.form["sluttid"]
        adress = request.form["adress"]
        kommentar = request.form.get("kommentar", "")
        new_row = Schema(
            namn=namn,
            datum=datum,
            starttid=starttid,
            sluttid=sluttid,
            adress=adress,
            kommentar=kommentar,
        )
        db.session.add(new_row)
        db.session.commit()
        flash("Schemarad sparad.")
        send_push_to_all_users("📅 Nytt schema", f"{namn} är schemalagd {datum} {starttid}–{sluttid}")
        return redirect(url_for("admin.admin_schema"))

    anstallda = [r.namn for r in db.session.query(Schema.namn).distinct()]
    return render_template("admin_schema_add.html", anstallda=anstallda)

@admin_bp.route("/admin/schema/edit/<int:row_id>", methods=["GET", "POST"])
def admin_schema_edit(row_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    row = Schema.query.get(row_id)
    if not row:
        flash("Schemarad ej hittad.")
        return redirect(url_for("admin.admin_schema"))

    if request.method == "POST":
        row.namn = request.form["namn"]
        row.datum = request.form["datum"]
        row.starttid = request.form["starttid"]
        row.sluttid = request.form["sluttid"]
        row.adress = request.form["adress"]
        row.kommentar = request.form.get("kommentar", "")
        db.session.commit()
        flash("Schemarad uppdaterad.")
        send_push_to_all_users("📅 Schema ändrat", f"{row.namn}: {row.datum} {row.starttid}–{row.sluttid}")
        return redirect(url_for("admin.admin_schema"))

    columns = ["namn", "datum", "starttid", "sluttid", "adress", "kommentar"]
    row_dict = {
        "namn": row.namn,
        "datum": row.datum,
        "starttid": row.starttid,
        "sluttid": row.sluttid,
        "adress": row.adress,
        "kommentar": row.kommentar,
    }
    return render_template("admin_schema_edit.html", row=row_dict, columns=columns)

@admin_bp.route("/admin/schema/delete/<int:row_id>", methods=["POST"])
def admin_schema_delete(row_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    row = Schema.query.get(row_id)
    if row:
        db.session.delete(row)
        db.session.commit()
        flash("Schemarad raderad.")
        send_push_to_all_users("📅 Schema raderat", f"{row.namn} hade ett schema på {row.datum} som nu är borttaget")
    return redirect(url_for("admin.admin_schema"))

@admin_bp.route("/admin/export")
def admin_export():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    entries = Checkin.query.order_by(Checkin.checkin_time.desc()).all()
    data = [
        {
            "Namn": e.user,
            "Mobil": getattr(e, "mobil", ""),
            "Checkin": e.checkin_time,
            "Checkin-adress": e.checkin_address,
            "Checkout": e.checkout_time,
            "Checkout-adress": e.checkout_address,
            "Arbetad tid (minuter)": e.work_time_minutes,
        }
        for e in entries
    ]

    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)

    return send_file(output, download_name="admin_export.xlsx", as_attachment=True)


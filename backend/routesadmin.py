from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
from .models import db, Checkin, Schema  # OBS: Schema-modell måste finnas!
import pandas as pd
from io import BytesIO

admin_bp = Blueprint('admin', __name__)
ADMIN_PASSWORD = "19890108"  # Byt detta!

# ---------------- Inloggning & utloggning ----------------

@admin_bp.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('losenord', '')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['username'] = "Admin"
            return redirect(url_for('admin.admin_panel'))
        flash("Fel lösenord.")
    return render_template('admin_login.html')

@admin_bp.route('/admin-logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.admin_login'))

# ---------------- Panel ----------------

@admin_bp.route('/admin_panel')
def admin_panel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))
    return render_template('admin_panel.html')

@admin_bp.route('/admin/logg')
def admin_logg():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))

    entries = Checkin.query.order_by(Checkin.checkin_time.desc()).all()

    # Omvandla till list of dicts
    records = [e.to_dict() for e in entries]  # ← kräver to_dict() i modellen
    columns = records[0].keys() if records else []

    return render_template('admin_logg.html', records=records, columns=columns)


# ---------------- Visa logg ----------------

@admin_bp.route('/admin/history')
def admin_history():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))
    checkins = Checkin.query.order_by(Checkin.checkin_time.desc()).all()
    return render_template('admin_history.html', entries=checkins)

# ---------------- Redigera post ----------------

@admin_bp.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
def admin_edit(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))

    entry = Checkin.query.get(id)
    if not entry:
        flash("Post ej hittad.")
        return redirect(url_for('admin.admin_history'))

    if request.method == 'POST':
        entry.checkin_time = request.form['checkin_time']
        entry.checkout_time = request.form['checkout_time']
        entry.checkin_address = request.form['checkin_address']
        entry.checkout_address = request.form['checkout_address']
        try:
            entry.work_time_minutes = int(request.form['work_time_minutes'])
        except:
            entry.work_time_minutes = None
        db.session.commit()
        flash("Post uppdaterad.")
        return redirect(url_for('admin.admin_history'))

    return render_template('admin_edit.html', entry=entry)

# ---------------- Radera post ----------------

@admin_bp.route('/admin/delete/<int:id>', methods=['POST'])
def admin_delete(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))
    entry = Checkin.query.get(id)
    if entry:
        db.session.delete(entry)
        db.session.commit()
        flash("Post raderad.")
    return redirect(url_for('admin.admin_history'))

# ---------------- Visa alla scheman ----------------

@admin_bp.route('/admin/schema')
def admin_schema():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))

    records = Schema.query.order_by(Schema.datum.desc()).all()
    columns = ['id', 'namn', 'datum', 'starttid', 'sluttid', 'adress', 'kommentar']
    # Gör records till listor av dicts så det funkar med {{ rad[col] }} i HTML
    record_dicts = [
        {
            'id': r.id,
            'namn': r.namn,
            'datum': r.datum,
            'starttid': r.starttid,
            'sluttid': r.sluttid,
            'adress': r.adress,
            'kommentar': r.kommentar
        } for r in records
    ]
    return render_template('admin_schema.html', records=record_dicts, columns=columns)


# ---------------- Lägg till schema ----------------

@admin_bp.route('/admin/schema/add', methods=['GET', 'POST'])
def admin_schema_add():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))

    if request.method == 'POST':
        namn = request.form['namn']
        datum = request.form['datum']
        starttid = request.form['starttid']
        sluttid = request.form['sluttid']
        adress = request.form['adress']  # <-- ÄNDRAT!
        kommentar = request.form.get('kommentar', '')
        new_row = Schema(
            namn=namn,
            datum=datum,
            starttid=starttid,
            sluttid=sluttid,
            adress=adress,  # <-- ÄNDRAT!
            kommentar=kommentar
        )
        db.session.add(new_row)
        db.session.commit()
        flash("Schemarad sparad.")
        return redirect(url_for('admin.admin_schema'))

    anstallda = [r.namn for r in db.session.query(Schema.namn).distinct()]
    return render_template('admin_schema_add.html', anstallda=anstallda)


# ---------------- Redigera schema ----------------

@admin_bp.route('/admin/schema/edit/<int:row_id>', methods=['GET', 'POST'])
def admin_schema_edit(row_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))

    row = Schema.query.get(row_id)
    if not row:
        flash("Schemarad ej hittad.")
        return redirect(url_for('admin.admin_schema'))

    if request.method == 'POST':
        row.namn = request.form['namn']
        row.datum = request.form['datum']
        row.starttid = request.form['starttid']
        row.sluttid = request.form['sluttid']
        row.adress = request.form['adress']  # ÄNDRAT
        row.kommentar = request.form.get('kommentar', '')
        db.session.commit()
        flash("Schemarad uppdaterad.")
        return redirect(url_for('admin.admin_schema'))

    # Uppdatera columns och row-dict så det matchar modellen
    columns = ['namn', 'datum', 'starttid', 'sluttid', 'adress', 'kommentar']
    row_dict = {
        'namn': row.namn,
        'datum': row.datum,
        'starttid': row.starttid,
        'sluttid': row.sluttid,
        'adress': row.adress,
        'kommentar': row.kommentar
    }
    return render_template('admin_schema_edit.html', row=row_dict, columns=columns)


# ---------------- Radera schema ----------------

@admin_bp.route('/admin/schema/delete/<int:row_id>', methods=['POST'])
def admin_schema_delete(row_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))

    row = Schema.query.get(row_id)
    if row:
        db.session.delete(row)
        db.session.commit()
        flash("Schemarad raderad.")
    return redirect(url_for('admin.admin_schema'))

# ---------------- Exportera till Excel ----------------

@admin_bp.route('/admin/export')
def admin_export():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))
    
    entries = Checkin.query.order_by(Checkin.checkin_time.desc()).all()
    data = [{
        'Namn': e.user,
        'Mobil': e.mobil,
        'Checkin': e.checkin_time,
        'Checkin-adress': e.checkin_address,
        'Checkout': e.checkout_time,
        'Checkout-adress': e.checkout_address,
        'Arbetad tid (minuter)': e.work_time_minutes
    } for e in entries]

    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    return send_file(output, download_name='admin_export.xlsx', as_attachment=True)

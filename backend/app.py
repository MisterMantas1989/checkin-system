from flask import Flask, render_template, request, redirect, url_for, session, flash, g

import sqlite3
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim
from openpyxl import load_workbook
import os

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('chat.db')
        g.db.row_factory = sqlite3.Row
    return g.db

app = Flask(__name__)
app.secret_key = 'MantasVanagas1989'
ADMIN_PASSWORD = '19890108'
XLSX_FILE = 'logg.xlsx'

HEADERS = [
    'Namn', 'Mobil',
    'Checkin-datum', 'Checkin-tid', 'Checkin-adress',
    'Checkout-datum', 'Checkout-tid', 'Checkout-adress',
    'Total tid (minuter)'
]

# Skapa Excel-fil om den inte finns
if not os.path.isfile(XLSX_FILE):
    df = pd.DataFrame(columns=HEADERS)
    df.to_excel(XLSX_FILE, index=False, engine='openpyxl')

def get_street_address(lat, lon):
    geolocator = Nominatim(user_agent="checkin_system")
    try:
        location = geolocator.reverse((lat, lon), language='sv')
        if location:
            addr = location.raw.get('address', {})
            street = addr.get('road', '')
            number = addr.get('house_number', '')
            city = addr.get('city', '') or addr.get('town', '') or addr.get('village', '')
            return f"{street} {number}, {city}".strip(', ')
        return "Okänd adress"
    except Exception:
        return "GPS-fel"

def autosize_columns():
    wb = load_workbook(XLSX_FILE)
    ws = wb.active
    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        ws.column_dimensions[col_letter].width = max_length + 2
    wb.save(XLSX_FILE)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        namn = request.form.get('namn', '').strip()
        mobil = request.form.get('mobil', '').strip().zfill(10)
        if namn and mobil:
            # Spara namn i sessionen direkt efter inloggning!
            session['username'] = namn
            # Du kan också spara mobil om du vill:
            # session['usermobile'] = mobil
            return redirect(url_for('checkin', namn=namn, mobil=mobil))
        return render_template('login.html', error="Ange både namn och mobilnummer")
    return render_template('login.html')
@app.route('/checkin', methods=['GET', 'POST'])
def checkin():
    namn = request.args.get('namn', '').strip()
    mobil = request.args.get('mobil', '').strip().zfill(10)
    if request.method == 'POST':
        try:
            lat = float(request.form.get('lat', ''))
            lon = float(request.form.get('lon', ''))
        except ValueError:
            return render_template('done.html', message="Ogiltiga GPS-koordinater vid incheckning!")

        now = datetime.now()
        in_date = now.strftime('%Y-%m-%d')
        in_time = now.strftime('%H:%M:%S')
        address = get_street_address(lat, lon)

        # Spara till Excel som förut
        df = pd.read_excel(XLSX_FILE, engine='openpyxl')
        df['Mobil'] = df['Mobil'].astype(str).str.zfill(10)
        mask = (df['Namn'].str.strip() == namn) & (df['Mobil'] == mobil) & (df['Checkout-datum'].isna() | (df['Checkout-datum'] == ''))

        if mask.any():
            return render_template('done.html', message=f"{namn}, du är redan incheckad. Checka ut först.")

        new_row = {
            'Namn': namn,
            'Mobil': mobil,
            'Checkin-datum': in_date,
            'Checkin-tid': in_time,
            'Checkin-adress': address,
            'Checkout-datum': '',
            'Checkout-tid': '',
            'Checkout-adress': '',
            'Total tid (minuter)': ''
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_excel(XLSX_FILE, index=False, engine='openpyxl')
        autosize_columns()
        
        # --------- NYTT: Lägg in i SQLite-databasen ----------
        import sqlite3
        db_path = os.path.join(os.path.dirname(__file__), 'chat.db')
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO checkins 
            (user, checkin_time, checkin_address, checkout_time, checkout_address, work_time_minutes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (namn, f"{in_date} {in_time}", address, None, None, None))
        conn.commit()
        conn.close()
        # ------------------------------------------------------

        return render_template('done.html',
            message=f'Du är nu incheckad. Välkommen {namn}!',
            namn=namn, mobil=mobil, show_checkout=True)
    return render_template('checkin.html', namn=namn, mobil=mobil)
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    namn = request.args.get('namn', '').strip()
    mobil = request.args.get('mobil', '').strip().zfill(10)
    if request.method == 'POST':
        try:
            lat = float(request.form.get('lat', ''))
            lon = float(request.form.get('lon', ''))
        except ValueError:
            return render_template('done.html', message="Ogiltiga GPS-koordinater vid utcheckning!")

        now = datetime.now()
        out_date = now.strftime('%Y-%m-%d')
        out_time = now.strftime('%H:%M:%S')
        address = get_street_address(lat, lon)

        df = pd.read_excel(XLSX_FILE, engine='openpyxl')
        df['Mobil'] = df['Mobil'].astype(str).str.zfill(10)

        mask = (df['Namn'].str.strip() == namn) & (df['Mobil'] == mobil) & (df['Checkout-datum'].isna() | (df['Checkout-datum'] == ''))

        if not mask.any():
            return render_template('done.html', message="Ingen aktiv incheckning att checka ut från!")

        idx = df[mask].index[-1]
        in_str = f"{df.loc[idx, 'Checkin-datum']} {df.loc[idx, 'Checkin-tid']}"
        in_dt = datetime.strptime(in_str, '%Y-%m-%d %H:%M:%S')
        total_minutes = int((now - in_dt).total_seconds() // 60)

        df.loc[idx, 'Checkout-datum'] = out_date
        df.loc[idx, 'Checkout-tid'] = out_time
        df.loc[idx, 'Checkout-adress'] = address
        df.loc[idx, 'Total tid (minuter)'] = total_minutes

        # Summera all tid samma dag, samma person
        df['Total arbetad tid idag'] = ""
        today_mask = (df['Namn'].str.strip() == namn) & (df['Mobil'] == mobil) & (df['Checkin-datum'] == out_date)
        total_today = df.loc[today_mask, 'Total tid (minuter)'].fillna(0).astype(int).sum()
        df.loc[today_mask, 'Total arbetad tid idag'] = total_today

        df.to_excel(XLSX_FILE, index=False, engine='openpyxl')
        autosize_columns()

        # -------- NYTT: Uppdatera SQLite-databas --------
        import sqlite3
        db_path = os.path.join(os.path.dirname(__file__), 'chat.db')
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, checkin_time FROM checkins 
            WHERE user=? AND (checkout_time IS NULL OR checkout_time = '') AND checkin_time IS NOT NULL
            ORDER BY checkin_time DESC LIMIT 1
        """, (namn,))
        row = cur.fetchone()
        if row:
            checkin_id = row[0]
            cur.execute("""
                UPDATE checkins
                SET checkout_time=?, checkout_address=?, work_time_minutes=?
                WHERE id=?
            """, (f"{out_date} {out_time}", address, total_minutes, checkin_id))
            conn.commit()
        conn.close()
        # -----------------------------------------------

        return render_template('done.html', message=f'Tack för idag, {namn}!')
    return render_template('checkout.html', namn=namn, mobil=mobil)
@app.route('/schema')
def visa_schema():
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.xlsx')
    if not os.path.exists(schema_path):
        return "Schemafilen saknas!"
    try:
        df = pd.read_excel(schema_path, sheet_name='Sheet1')
    except Exception as e:
        return f"Fel vid läsning av schemafilen: {e}"
    df = df.dropna(how='all').fillna("")
    namn = request.args.get('namn', '').strip().lower()
    if namn and 'Namn' in df.columns:
        df = df[df['Namn'].str.strip().str.lower() == namn]
    if 'Datum' in df.columns:
        try:
            df['Datum'] = pd.to_datetime(df['Datum']).dt.strftime('%Y-%m-%d')
        except Exception:
            pass
    def format_tid(tid):
        if isinstance(tid, str) and ":" in tid:
            return tid
        try:
            tid_float = float(tid)
            timmar = int(tid_float)
            minuter = int(round((tid_float - timmar) * 60))
            return f"{timmar:02d}:{minuter:02d}"
        except:
            return str(tid)
    if 'Starttid' in df.columns:
        df['Starttid'] = df['Starttid'].apply(format_tid)
    if 'Sluttid' in df.columns:
        df['Sluttid'] = df['Sluttid'].apply(format_tid)
    schema_lista = df.to_dict(orient='records')
    kolumner = list(df.columns)
    if not schema_lista:
        return "Inget schema hittades för den angivna sökningen."
    return render_template('schema.html', records=schema_lista, columns=kolumner)
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('start'))
# ------------------ ADMIN -------------------

@app.route('/admin_panel')
def admin_panel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin_panel.html')

@app.route('/admin-schema')
def admin_schema():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.xlsx')
    if not os.path.exists(schema_path):
        return "Schemafilen saknas!"
    df = pd.read_excel(schema_path, sheet_name='Sheet1')
    df = df.dropna(how='all').fillna("")

    # Formatera datum och tider
    if 'Datum' in df.columns:
        df['Datum'] = pd.to_datetime(df['Datum']).dt.strftime('%Y-%m-%d')

    def format_tid(val):
        if pd.isna(val):
            return ''
        val = str(val).replace('.', ':')
        if ':' in val:
            parts = val.split(':')
            return f"{parts[0].zfill(2)}:{parts[1].ljust(2,'0')[:2]}"
        else:
            return f"{int(float(val)):02d}:00"
    if 'Starttid' in df.columns:
        df['Starttid'] = df['Starttid'].apply(format_tid)
    if 'Sluttid' in df.columns:
        df['Sluttid'] = df['Sluttid'].apply(format_tid)

    df['row_id'] = range(len(df))    # <-- NY RAD!

    schema_lista = df.to_dict(orient='records')
    kolumner = list(df.columns)
    return render_template('admin_schema.html', records=schema_lista, columns=kolumner)

@app.route('/admin-logg')
def admin_logg():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    logg_path = os.path.join(os.path.dirname(__file__), 'logg.xlsx')
    if not os.path.exists(logg_path):
        return "Loggfil saknas!"
    df = pd.read_excel(logg_path)
    df = df.dropna(how='all').fillna("")
    logg_lista = df.to_dict(orient='records')  # <-- DENNA RAD!
    kolumner = list(df.columns)
    return render_template('logg.html', records=logg_lista, columns=kolumner)
@app.route('/admin-logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))
@app.route('/admin-schema-add', methods=['GET', 'POST'])
def admin_schema_add():
    # Lägg till dina 5 anställda namn här:
    anstallda = ['Mantas Vanagas', 'Namn 2', 'Namn 3', 'Namn 4', 'Namn 5']
    message = ''
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        namn = request.form.get('namn', '').strip()
        datum = request.form.get('datum', '')
        starttid = request.form.get('starttid', '')
        sluttid = request.form.get('sluttid', '')
        plats = request.form.get('plats', '')
        kommentar = request.form.get('kommentar', '')

        # Skriv till schema.xlsx
        import pandas as pd
        import os
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.xlsx')
        # Läs in existerande fil, annars skapa ny
        if os.path.exists(schema_path):
            df = pd.read_excel(schema_path, sheet_name='Sheet1')
        else:
            df = pd.DataFrame(columns=['Namn','Datum','Starttid','Sluttid','Plats','Kommentar'])

        # Lägg till ny rad
        ny_rad = {
            'Namn': namn,
            'Datum': datum,
            'Starttid': starttid,
            'Sluttid': sluttid,
            'Plats': plats,
            'Kommentar': kommentar
        }
        df = pd.concat([df, pd.DataFrame([ny_rad])], ignore_index=True)
        df.to_excel(schema_path, index=False)

        message = "Schemarad tillagd!"

    return render_template('admin_schema_add.html', anstallda=anstallda, message=message)
@app.route('/admin-schema/edit/<int:row_id>', methods=['GET', 'POST'])
def admin_schema_edit(row_id):
    # Din kod för att visa och spara ändrad rad
    import pandas as pd
    import os
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.xlsx')
    df = pd.read_excel(schema_path, sheet_name='Sheet1')
    df = df.dropna(how='all').fillna("")
    if request.method == 'POST':
        for col in df.columns:
            if col != 'row_id':  # Ändra inte row_id
                df.at[row_id, col] = request.form.get(col, "")
        df.to_excel(schema_path, index=False)
        return redirect(url_for('admin_schema'))
    row = df.iloc[row_id]
    columns = list(df.columns)
    return render_template('admin_schema_edit.html', row=row, columns=columns, row_id=row_id)
@app.route('/admin-schema/delete/<int:row_id>', methods=['POST'])
def admin_schema_delete(row_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    import pandas as pd
    import os
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.xlsx')
    df = pd.read_excel(schema_path, sheet_name='Sheet1')
    df = df.dropna(how='all').fillna("")
    if 0 <= row_id < len(df):
        df = df.drop(df.index[row_id])
        df.reset_index(drop=True, inplace=True)
        df.to_excel(schema_path, index=False)
    return redirect(url_for('admin_schema'))
# ------- Databasanslutning --------
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('chat.db')
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('losenord', '')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['username'] = "Mantas Vanagas" 
            return redirect(url_for('admin_panel'))
        else:
            flash('Fel lösenord!')
    return render_template('admin_login.html')

# --- Chat: Visa och lägg till meddelande ---
@app.route('/chat', methods=['GET', 'POST'])
def chat():
    db = get_db()
    if 'username' not in session:
        session['username'] = 'Admin'

    if request.method == 'POST':
        user = session.get('username', 'Admin')
        msg = request.form.get('message', '').strip()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if msg:
            db.execute(
                'INSERT INTO messages (user, message, timestamp) VALUES (?, ?, ?)',
                (user, msg, timestamp)
            )
            db.commit()
    messages = db.execute('SELECT * FROM messages ORDER BY timestamp DESC').fetchall()
    return render_template('admin_chat.html', messages=messages)
@app.route('/chat2', methods=['GET', 'POST'])
def employee_chat():
    db = get_db()
    if 'username' not in session:
        session['username'] = 'Anonym'
    user = session.get('username', 'Anonym')

    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if message:
            db.execute(
                "INSERT INTO messages (user, message, timestamp) VALUES (?, ?, ?)",
                (user, message, timestamp)
            )
            db.commit()
        return redirect(url_for('employee_chat'))

    messages = db.execute("SELECT * FROM messages ORDER BY timestamp DESC").fetchall()
    return render_template('chat.html', messages=messages)

# --- Chat: Radera meddelande ---
@app.route('/chat/delete/<int:msg_id>', methods=['POST'])
def chat_delete(msg_id):
    if not session.get('admin_logged_in'):
        return "Endast admin kan radera meddelanden!", 403
    db = get_db()
    db.execute('DELETE FROM messages WHERE id = ?', (msg_id,))
    db.commit()
    return redirect(url_for('chat'))

# --- Chat: Redigera meddelande ---
@app.route('/chat/edit/<int:msg_id>', methods=['GET', 'POST'])
def chat_edit(msg_id):
    db = get_db()
    if request.method == 'POST':
        new_msg = request.form.get('message', '').strip()
        db.execute('UPDATE messages SET message = ? WHERE id = ?', (new_msg, msg_id))
        db.commit()
        return redirect(url_for('chat'))
    msg = db.execute('SELECT * FROM messages WHERE id = ?', (msg_id,)).fetchone()
    return render_template('chat_edit.html', msg=msg)
if __name__ == '__main__':
    app.run(debug=True)



























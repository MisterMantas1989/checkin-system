from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import sqlite3
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim
from openpyxl import load_workbook
from backend.fix_db import init_messages_table, save_message, get_messages
import os

def init_checkins_table():
    db_path = os.path.join(os.path.dirname(__file__), 'chat.db')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            mobil TEXT,
            checkin_time TEXT,
            checkin_address TEXT,
            checkout_time TEXT,
            checkout_address TEXT,
            work_time_minutes INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('chat.db')
        g.db.row_factory = sqlite3.Row
    return g.db

app = Flask(__name__)
app.secret_key = 'MantasVanagas1989'
ADMIN_PASSWORD = '19890108'
XLSX_FILE = 'checkin_data.xlsx'
HEADERS = [
    'Namn', 'Mobil',
    'Checkin-datum', 'Checkin-tid', 'Checkin-adress',
    'Checkout-datum', 'Checkout-tid', 'Checkout-adress',
    'Total tid (minuter)', 'Total arbetad tid idag'
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
        # Validera mobilnummer
        if not (namn and mobil.isdigit() and len(mobil) == 10):
            return render_template('login.html', error="Ange både namn och giltigt 10-siffrigt mobilnummer")
        session['username'] = namn
        session['usermobile'] = mobil
        return redirect(url_for('checkin'))
    return render_template('login.html')

@app.route('/checkin', methods=['GET', 'POST'])
def checkin():
    namn = session.get('username', '')
    mobil = session.get('usermobile', '')
    if not namn or not mobil:
        return redirect(url_for('login'))

    # Läs in Excel-filen
    df = pd.read_excel(XLSX_FILE, engine='openpyxl')
    df['Mobil'] = df['Mobil'].astype(str).str.zfill(10)

    # Kolla om redan incheckad
    mask = (df['Namn'].str.strip() == namn) & (df['Mobil'] == mobil) & (
        df['Checkout-datum'].isna() | (df['Checkout-datum'] == '')
    )

    if mask.any() and request.method == 'GET':
        return render_template('done.html',
            message=f"{namn}, du är redan incheckad!",
            show_checkout=True
        )

    if request.method == 'POST':
        if mask.any():
            return render_template('done.html',
                message=f"{namn}, du är redan incheckad!",
                show_checkout=True
            )
        try:
            lat = float(request.form.get('lat', ''))
            lon = float(request.form.get('lon', ''))
        except ValueError:
            return render_template('done.html', message="Ogiltiga GPS-koordinater vid incheckning!")

        now = datetime.now()
        in_date = now.strftime('%Y-%m-%d')
        in_time = now.strftime('%H:%M:%S')
        address = get_street_address(lat, lon)

        new_row = {
            'Namn': namn,
            'Mobil': mobil,
            'Checkin-datum': in_date,
            'Checkin-tid': in_time,
            'Checkin-adress': address,
            'Checkout-datum': '',
            'Checkout-tid': '',
            'Checkout-adress': '',
            'Total tid (minuter)': '',
            'Total arbetad tid idag': ''
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_excel(XLSX_FILE, index=False, engine='openpyxl')
        autosize_columns()

        # Logga till SQLite
        try:
            db_path = os.path.join(os.path.dirname(__file__), 'chat.db')
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            # Skapa tabell om den inte finns
            cur.execute("""
                CREATE TABLE IF NOT EXISTS checkins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user TEXT,
                    mobil TEXT,
                    checkin_time TEXT,
                    checkin_address TEXT,
                    checkout_time TEXT,
                    checkout_address TEXT,
                    work_time_minutes INTEGER
                )
            """)

            # Infoga data
            cur.execute("""
                INSERT INTO checkins 
                (user, mobil, checkin_time, checkin_address, checkout_time, checkout_address, work_time_minutes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (namn, mobil, f"{in_date} {in_time}", address, None, None, None))

            conn.commit()

        except Exception as e:
            print("SQLite Error:", e)
            traceback.print_exc()
        finally:
            conn.close()

        return render_template('done.html',
            message=f'Du är nu incheckad. Välkommen {namn}!',
            show_checkout=True
        )

    return render_template('checkin.html', namn=namn, mobil=mobil)
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    namn = session.get('username', '')
    mobil = session.get('usermobile', '')
    if not namn or not mobil:
        return redirect(url_for('login'))

    df = pd.read_excel(XLSX_FILE, engine='openpyxl')
    df['Mobil'] = df['Mobil'].astype(str).str.zfill(10)

    mask = (df['Namn'].str.strip() == namn) & (df['Mobil'] == mobil) & (
        df['Checkout-datum'].isna() | (df['Checkout-datum'] == '')
    )

    if not mask.any():
        return render_template('done.html', message="Ingen aktiv incheckning att checka ut från!")

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

        idx = df[mask].index[-1]
        in_str = f"{df.loc[idx, 'Checkin-datum']} {df.loc[idx, 'Checkin-tid']}"
        in_dt = datetime.strptime(in_str, '%Y-%m-%d %H:%M:%S')
        total_minutes = int((now - in_dt).total_seconds() // 60)

        # Uppdatera Excel
        df.loc[idx, 'Checkout-datum'] = out_date
        df.loc[idx, 'Checkout-tid'] = out_time
        df.loc[idx, 'Checkout-adress'] = address
        df.loc[idx, 'Total tid (minuter)'] = total_minutes

        today_mask = (df['Namn'].str.strip() == namn) & (df['Mobil'] == mobil) & (df['Checkin-datum'] == out_date)
        total_today = df.loc[today_mask, 'Total tid (minuter)'].fillna(0).astype(int).sum()
        df.loc[today_mask, 'Total arbetad tid idag'] = total_today

        df.to_excel(XLSX_FILE, index=False, engine='openpyxl')
        autosize_columns()

        # Uppdatera SQLite
        try:
            db_path = os.path.join(os.path.dirname(__file__), 'chat.db')
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            # Försäkra att tabellen existerar
            cur.execute("""
                CREATE TABLE IF NOT EXISTS checkins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user TEXT,
                    mobil TEXT,
                    checkin_time TEXT,
                    checkin_address TEXT,
                    checkout_time TEXT,
                    checkout_address TEXT,
                    work_time_minutes INTEGER
                )
            """)

            # Leta upp senast aktiva incheckning
            cur.execute("""
                SELECT id FROM checkins 
                WHERE user=? AND mobil=? AND (checkout_time IS NULL OR checkout_time = '')
                ORDER BY checkin_time DESC LIMIT 1
            """, (namn, mobil))
            row = cur.fetchone()
            if row:
                checkin_id = row[0]
                cur.execute("""
                    UPDATE checkins
                    SET checkout_time=?, checkout_address=?, work_time_minutes=?
                    WHERE id=?
                """, (f"{out_date} {out_time}", address, total_minutes, checkin_id))
                conn.commit()
        except Exception as e:
            print("SQLite Checkout Error:", e)
            traceback.print_exc()
        finally:
            conn.close()

        return render_template('done.html', message=f'Tack för idag, {namn}!')

    return render_template('checkout.html')@app.route('/history')
def history():
    namn = session.get('username', '')
    mobil = session.get('usermobile', '')
    if not namn or not mobil:
        return redirect(url_for('login'))

    try:
        df = pd.read_excel(XLSX_FILE, engine='openpyxl')
        df = df[(df['Namn'].str.strip() == namn) & (df['Mobil'] == mobil)]
    except Exception:
        df = pd.DataFrame()

    return render_template('history.html', entries=df.to_dict(orient='records'))
@app.route('/history')
def history():
    namn = session.get('username', '')
    mobil = session.get('usermobile', '')
    if not namn or not mobil:
        return redirect(url_for('login'))

    # 1. Hämta Excel-historik
    excel_entries = []
    try:
        df = pd.read_excel(XLSX_FILE, engine='openpyxl')
        df['Mobil'] = df['Mobil'].astype(str).str.zfill(10)
        user_history = df[(df['Namn'].str.strip() == namn) & (df['Mobil'] == mobil)]
        excel_entries = user_history.to_dict(orient='records')
    except Exception as e:
        print("Excel error:", e)

    # 2. Hämta SQLite-historik
    sqlite_entries = []
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'chat.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM checkins
            WHERE user=? AND mobil=?
            ORDER BY checkin_time DESC
        """, (namn, mobil))
        sqlite_entries = [dict(row) for row in cur.fetchall()]
        conn.close()
    except Exception as e:
        print("SQLite error:", e)

    # 3. Slå ihop båda listorna
    all_entries = []

    # Lägg till källa så du kan visa varifrån raden kommer om du vill
    for e in excel_entries:
        e['källa'] = 'Excel'
        all_entries.append(e)
    for e in sqlite_entries:
        e['källa'] = 'SQLite'
        all_entries.append(e)

    # 4. Sortera på incheckningstid/datum, nyaste först
    def get_sort_key(e):
        # Försök använda SQLite-fält om de finns, annars Excel-fält
        if 'checkin_time' in e and e['checkin_time']:
            return e['checkin_time']
        elif 'Checkin-datum' in e and 'Checkin-tid' in e:
            return f"{e['Checkin-datum']} {e['Checkin-tid']}"
        else:
            return ''
    all_entries.sort(key=get_sort_key, reverse=True)

    return render_template('history.html', entries=all_entries)
@app.route('/schema')
def visa_schema():
    namn = session.get('username', '').strip()
    if not namn:
        return redirect(url_for('login'))

    schema_path = os.path.join(os.path.dirname(__file__), 'schema.xlsx')
    if not os.path.exists(schema_path):
        return "Schemafilen saknas!"

    try:
        df = pd.read_excel(schema_path, sheet_name='Sheet1')
    except Exception as e:
        return f"Fel vid läsning av schemafilen: {e}"

    df = df.dropna(how='all').fillna("")

    # Filtrera schema baserat på inloggat namn
    df = df[df['Namn'].str.strip().str.lower() == namn.lower()]

    # Omvandla datum & tid
    if 'Datum' in df.columns:
        try:
            df['Datum'] = pd.to_datetime(df['Datum']).dt.strftime('%Y-%m-%d')
        except:
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
        return "Inget schema hittades för den angivna användaren."

    return render_template('schema.html', records=schema_lista, columns=kolumner)
@app.route('/logout')
def logout():
    session.clear()
    return render_template('logout_confirm.html')  # visar bekräftelse

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

    records = []

    # 1. 📄 Läs från Excel
    excel_path = os.path.join(os.path.dirname(__file__), 'logg.xlsx')
    if os.path.exists(excel_path):
        df_excel = pd.read_excel(excel_path).dropna(how='all').fillna("")
        excel_data = df_excel.to_dict(orient='records')
        for r in excel_data:
            r["källa"] = "Excel"
        records.extend(excel_data)

    # 2. 💾 Läs från SQLite
    try:
        db = get_db()
        cursor = db.execute("""
            SELECT user, mobil, checkin_time, checkin_address,
                   checkout_time, checkout_address, work_time_minutes
            FROM checkins
        """)
        rows = cursor.fetchall()
        for row in rows:
            records.append({
                "Användare": row["user"],
                "Mobil": row["mobil"],
                "Checkin-tid": row["checkin_time"],
                "Checkin-adress": row["checkin_address"],
                "Checkout-tid": row["checkout_time"],
                "Checkout-adress": row["checkout_address"],
                "Tid (min)": row["work_time_minutes"],
                "källa": "SQLite"
            })
    except Exception as e:
        flash(f"Fel vid läsning från SQLite: {e}", "error")

    # 3. 🔤 Lista av alla kolumnnamn för tabellhuvud
    alla_kolumner = sorted(set().union(*(r.keys() for r in records)))

    return render_template('admin_logg.html', records=records, columns=alla_kolumner)
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
    init_messages_table()
    user = session.get('username') or 'Admin'
    session['username'] = user

    if request.method == 'POST':
        msg = request.form.get('message', '').strip()
        if msg:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_message(user, msg, timestamp)
        return redirect(url_for('chat'))

    messages = get_messages()
    return render_template('admin_chat.html', messages=messages)

@app.route('/chat2', methods=['GET', 'POST'])
def employee_chat():
    init_messages_table()
    user = session.get('username') or 'Anonym'
    session['username'] = user

    if request.method == 'POST':
        msg = request.form.get('message', '').strip()
        if msg:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_message(user, msg, timestamp)
        return redirect(url_for('employee_chat'))

    messages = get_messages()
    return render_template('chat.html', messages=messages)

    messages = get_messages()
    return render_template('chat.html', messages=messages)# --- Chat: Radera meddelande ---
@app.route('/chat/delete/<int:msg_id>', methods=['POST'])
def chat_delete(msg_id):
    if not session.get('admin_logged_in'):
        return "Endast admin kan radera meddelanden!", 403
    db = get_db()
    db.execute('DELETE FROM messages WHERE id = ?', (msg_id,))
    db.commit()
    flash("Meddelandet raderat.")
    return redirect(url_for('chat'))

@app.route('/chat/edit/<int:msg_id>', methods=['GET', 'POST'])
def chat_edit(msg_id):
    if not session.get('admin_logged_in'):
        return "Endast admin kan redigera meddelanden!", 403

    db = get_db()
    msg = db.execute('SELECT * FROM messages WHERE id = ?', (msg_id,)).fetchone()
    if not msg:
        flash("Meddelandet finns inte.")
        return redirect(url_for('chat'))

    if request.method == 'POST':
        new_msg = request.form.get('message', '').strip()
        if not new_msg:
            flash("Meddelandet kan inte vara tomt.")
            return render_template('chat_edit.html', msg=msg)
        db.execute('UPDATE messages SET message = ? WHERE id = ?', (new_msg, msg_id))
        db.commit()
        flash("Meddelandet har ändrats.")
        return redirect(url_for('chat'))
    return render_template('chat_edit.html', msg=msg)
@app.route('/done-chat', methods=['POST'])
def send_chat_message():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = session['username']
    msg = request.form.get('message', '').strip()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()

    # Skapa tabellen bara om den inte finns (detta kan ligga i app-start eller separat init)
    db.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            message TEXT,
            timestamp TEXT
        )
    ''')
    db.commit()

    if msg:
        db.execute(
            'INSERT INTO messages (user, message, timestamp) VALUES (?, ?, ?)',
            (user, msg, timestamp)
        )
        db.commit()

    # Ladda om meddelanden
    messages = db.execute("SELECT * FROM messages ORDER BY timestamp DESC").fetchall()

    return render_template('done.html',
        message=f'Du är nu incheckad. Välkommen {user}!',
        show_checkout=True,
        messages=messages
    )


if __name__ == '__main__':
    app.run(debug=True)



























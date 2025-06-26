from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import os
import csv

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

LOG_DIR = os.path.join(os.getcwd(), "RVL_RASA_LOGGAR")
os.makedirs(LOG_DIR, exist_ok=True)

def get_log_path(name, date_str):
    safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).rstrip()
    return os.path.join(LOG_DIR, f"{safe_name}_{date_str}.csv")

@app.route('/')
def root():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/check', methods=['POST'])
def check():
    data = request.json
    name = data.get("name")
    status = data.get("status")  # 'in' eller 'ut'
    lat = data.get("lat")
    lon = data.get("lon")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str = datetime.now().strftime("%Y-%m-%d")
    filepath = get_log_path(name, date_str)

    row = [status, name, timestamp, lat, lon]

    if status == "ut":
        # Räkna tid mellan in och ut
        try:
            with open(filepath, 'r') as f:
                reader = list(csv.reader(f))
                checkins = [r for r in reversed(reader) if r[0] == "in"]
                if checkins:
                    last_in_time = datetime.strptime(checkins[0][2], "%Y-%m-%d %H:%M:%S")
                    time_spent = datetime.now() - last_in_time
                    row.append(str(time_spent))
        except Exception as e:
            row.append("")

    with open(filepath, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(row)

    return jsonify({"message": "Logg sparad"}), 200

@app.route('/logs/<date>', methods=['GET'])
def get_logs(date):
    logs = []
    for file in os.listdir(LOG_DIR):
        if file.endswith(f"{date}.csv"):
            with open(os.path.join(LOG_DIR, file), 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    logs.append({
                        "status": row[0],
                        "name": row[1],
                        "timestamp": row[2],
                        "lat": row[3],
                        "lon": row[4],
                        "total_time": row[5] if len(row) > 5 else ""
                    })
    return jsonify(logs)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)





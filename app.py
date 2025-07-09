from config import SQLALCHEMY_DATABASE_URI
from flask import Flask, redirect, request
from flask_cors import CORS
from flask_migrate import Migrate
from models import db
import os

# 🔹 Blueprints – Webbgränssnitt
from routesauth import auth_bp
from routesadmin import admin_bp
from routeschat import chat_bp
from routescheckin import checkin_bp
from routeshistory import history_bp

# 🔹 Blueprints – API för mobil/extern access
from api_auth import api_auth_bp
from api_checkin import api_checkin_bp
from api_misc import api_misc_bp
from api_chat import api_chat_bp
from api_user import api_user_bp  # 🆕 IMPORT – för login/register

# 🔧 Initiera Flask-app
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback_dev_key")
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ✅ Aktivera CORS – behövs om frontend körs från mobil/expo/webb
CORS(app, supports_credentials=True)

# 🛠 Initiera databas
db.init_app(app)

# 🆕 Lägg till Migrate
migrate = Migrate(app, db)

# 📡 Logga inkommande API-anrop för felsökning
@app.before_request
def log_request_info():
    print("\n🔹 API-anrop mottaget:")
    print(f"  ➤ Metod: {request.method}")
    print(f"  ➤ URL: {request.url}")
    print(f"  ➤ Headers: {dict(request.headers)}")
    print(f"  ➤ Body: {request.get_data(as_text=True)}")

# 🔌 Registrera Blueprints – Webbgränssnitt
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(checkin_bp)
app.register_blueprint(history_bp)

# 🔌 Registrera API-Blueprints – Mobilaccess
app.register_blueprint(api_auth_bp)
app.register_blueprint(api_checkin_bp)
app.register_blueprint(api_misc_bp)
app.register_blueprint(api_chat_bp)
app.register_blueprint(api_user_bp)  # ✅ REGISTERA USER API

# 🌐 Root redirect
@app.route("/")
def index():
    return redirect("/login")

# ▶️ Starta servern
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000), 













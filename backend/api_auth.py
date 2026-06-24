from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from models import User, db
import uuid

api_auth_bp = Blueprint("api_auth", __name__)

# 🔍 TOKEN VERIFIERING
def get_user_from_token(request):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip()
    if not token:
        return None
    return User.query.filter_by(token=token).first()

# 🔐 LOGIN – FIXAD VERSION
@api_auth_bp.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    name = data.get("name")
    password = data.get("password")

    if not name or not password:
        return jsonify({"error": "Namn och lösenord krävs"}), 400

    user = User.query.filter_by(name=name).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Felaktigt användarnamn eller lösenord"}), 401

    token = str(uuid.uuid4())
    user.token = token
    db.session.commit()

    return jsonify({"token": token})


# 🔓 LOGOUT
@api_auth_bp.route("/api/logout", methods=["POST"])
def api_logout():
    user = get_user_from_token(request)
    if not user:
        return jsonify({"error": "Inte autentiserad"}), 401

    user.token = None
    db.session.commit()
    return jsonify({"message": "Utloggning OK"})






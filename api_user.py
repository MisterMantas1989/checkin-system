from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, db
import secrets
from api_auth import get_user_from_token

api_user_bp = Blueprint("api_user", __name__)

# ------------------ Registrering ------------------

@api_user_bp.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    name = data.get("name")
    password = data.get("password")

    if not name or not password:
        return jsonify({"error": "Namn och lösenord krävs"}), 400

    if User.query.filter_by(name=name).first():
        return jsonify({"error": "Användarnamn upptaget"}), 400

    password_hash = generate_password_hash(password)
    user = User(name=name, password_hash=password_hash)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Registrering klar"})

# ------------------ Inloggning ------------------

@api_user_bp.route("/api/login", methods=["POST"])
def login():
    try:
        print("\n🔵 DEBUG START /api/login ----------------------------")
        print("request.is_json:", request.is_json)
        print("request.content_type:", request.content_type)
        print("request.headers:", dict(request.headers))
        raw_data = request.get_data().decode("utf-8", errors="replace")
        print("RAW BODY:", raw_data)

        if not request.is_json:
            print("❌ INGEN JSON!")
            return jsonify({"error": "Förväntar JSON-data"}), 400

        try:
            data = request.get_json(force=True)
        except Exception as e:
            print("❌ JSON-PARSING ERROR:", str(e))
            return jsonify({"error": "Ogiltig JSON"}), 400

        print("✅ JSON mottagen:", data)

        name = data.get("name")
        password = data.get("password")
        push_token = data.get("pushToken")

        if not name or not password:
            print("❌ Saknar namn/lösenord")
            return jsonify({"error": "Namn och lösenord krävs"}), 400

        user = User.query.filter_by(name=name).first()

        if not user:
            print("❌ Användare ej hittad:", name)
            return jsonify({"error": "Användare finns ej"}), 404

        if not check_password_hash(user.password_hash, password):
            print("❌ Fel lösenord")
            return jsonify({"error": "Felaktigt lösenord"}), 401

        # Uppdatera push token om det skickas
        if push_token:
            user.push_token = push_token
            db.session.commit()
            print("✅ Push-token uppdaterad")

        print("✅ Inloggning lyckades")
        return jsonify({"token": user.token, "name": user.name}), 200

    except Exception as e:
        import traceback
        print("❌ INTERN FEL:", str(e))
        traceback.print_exc()
        return jsonify({"error": "Internt fel"}), 500


# ------------------ Hämta användarinfo ------------------

@api_user_bp.route("/api/me", methods=["GET"])
def me():
    user = get_user_from_token(request)
    if not user:
        return jsonify({"error": "Inte autentiserad"}), 401
    return jsonify({"name": user.name})

# ------------------ Manuellt spara push-token ------------------

@api_user_bp.route("/api/push-token", methods=["POST"])
def save_push_token():
    user = get_user_from_token(request)
    if not user:
        return jsonify({"error": "Inte autentiserad"}), 401

    data = request.get_json()
    token = data.get("token")

    if not token:
        return jsonify({"error": "Ingen token mottagen"}), 400

    user.push_token = token
    db.session.commit()

    return jsonify({"message": "Token sparad"})
 






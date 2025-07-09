from flask import Blueprint, request, jsonify
from models import db, Message
from datetime import datetime
from api_auth import get_user_from_token

api_chat_bp = Blueprint("api_chat", __name__)

@api_chat_bp.route("/api/messages", methods=["GET", "POST"])
def messages():
    print("🔹 [CHAT] API-anrop mottaget")
    user = get_user_from_token(request)
    print(f"🔐 Användare identifierad: {user.name if user else '❌ None'}")

    if not user:
        return jsonify({"error": "Inte autentiserad"}), 401

    if request.method == "POST":
        data = request.get_json()
        print("📨 POST-body:", data)

        if not data or not isinstance(data.get("message"), str) or not data["message"].strip():
            print("❌ Ogiltigt meddelandeformat")
            return jsonify({"error": "Meddelande saknas eller ogiltigt"}), 400

        try:
            msg = Message(
                user=user.name,
                message=data["message"].strip(),
                timestamp=datetime.utcnow()
            )

            db.session.add(msg)
            db.session.commit()

            print("✅ Meddelande sparat:", msg.message)

            return jsonify({
                "success": True,
                "message": {
                    "user": msg.user,
                    "message": msg.message,
                    "timestamp": msg.timestamp.isoformat()
                }
            })

        except Exception as e:
            print("🔥 DB-fel vid POST:", e)
            db.session.rollback()
            return jsonify({"error": "Fel vid sparning"}), 500

    # GET - hämta senaste 50 meddelanden, nyaste sist
    try:
        msgs = Message.query.order_by(Message.id.desc()).limit(50).all()
        msgs = list(reversed(msgs))  # så nyaste visas sist

        print(f"📥 {len(msgs)} meddelanden laddade")

        return jsonify({
            "messages": [
                {
                    "user": m.user,
                    "message": m.message,
                    "timestamp": (
                        m.timestamp.isoformat() if isinstance(m.timestamp, datetime) 
                        else str(m.timestamp)
                    )
                }
                for m in msgs
            ]
        })

    except Exception as e:
        print("🔥 Fel vid GET /api/messages:", e)
        return jsonify({"error": "Fel vid hämtning av meddelanden"}), 500





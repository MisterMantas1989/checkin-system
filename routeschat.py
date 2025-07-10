from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from models import Message, db
import pytz

chat_bp = Blueprint("chat", __name__)


from datetime import datetime
import pytz

@chat_bp.route("/chat", methods=["GET", "POST"])
def chat():
    user = session.get("username") or "Admin"
    session["username"] = user

    if request.method == "POST":
        msg = request.form.get("message", "").strip()
        if msg:
            db.session.add(
                Message(
                    user=user,
                    message=msg,
                    timestamp=datetime.now(pytz.timezone("Europe/Stockholm")).strftime("%Y-%m-%d %H:%M:%S"),
                )
            )
            db.session.commit()
        return redirect(url_for("chat.chat"))

    messages = Message.query.order_by(Message.timestamp.desc()).all()
    return render_template("admin_chat.html", messages=messages)

@chat_bp.route("/chat2", methods=["GET", "POST"])
def employee_chat():
    user = session.get("username") or "Anonym"
    session["username"] = user

    if request.method == "POST":
        msg = request.form.get("message", "").strip()
        if msg:
            db.session.add(
                Message(
                    user=user,
                    message=msg,
                    timestamp=datetime.now(pytz.timezone("Europe/Stockholm")).strftime("%Y-%m-%d %H:%M:%S"),
                )
            )
            db.session.commit()
        return redirect(url_for("chat.employee_chat"))

    messages = Message.query.order_by(Message.timestamp.desc()).all()
    return render_template("chat.html", messages=messages)

@chat_bp.route("/chat/delete/<int:msg_id>", methods=["POST"])
def chat_delete(msg_id):
    if not session.get("admin_logged_in"):
        return "Endast admin kan radera meddelanden!", 403

    msg = Message.query.get(msg_id)
    if msg:
        db.session.delete(msg)
        db.session.commit()
        flash("Meddelandet raderat.")
    return redirect(url_for("chat.chat"))

@chat_bp.route("/chat/edit/<int:msg_id>", methods=["GET", "POST"])
def chat_edit(msg_id):
    if not session.get("admin_logged_in"):
        return "Endast admin kan redigera meddelanden!", 403

    msg = Message.query.get(msg_id)
    if not msg:
        flash("Meddelandet finns inte.")
        return redirect(url_for("chat.chat"))

    if request.method == "POST":
        new_msg = request.form.get("message", "").strip()
        if not new_msg:
            flash("Meddelandet kan inte vara tomt.")
        else:
            msg.message = new_msg
            db.session.commit()
            flash("Meddelandet uppdaterat.")
        return redirect(url_for("chat.chat"))

    return render_template("chat_edit.html", msg=msg)

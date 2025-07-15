from flask import Blueprint, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash
from models import User
from datetime import timedelta

auth_bp = Blueprint("auth", __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        namn = request.form.get('namn')
        lösenord = request.form.get('lösenord')
        print("🔐 Inloggningstest med namn:", namn)

        if not namn or not lösenord:
            error = "Vänligen fyll i både namn och lösenord."
            return render_template('login.html', error=error), 400

        try:
            user = User.query.filter_by(name=namn).first()
        except Exception as e:
            print("❌ Fel vid databasfråga:", e)
            error = "Serverfel. Kontakta administratör."
            return render_template('login.html', error=error), 500

        if user:
            if check_password_hash(user.password_hash, lösenord):
                print("✅ Inloggning OK för användare:", user.name)

                # 🔒 Permanent session aktiverad
                session.permanent = True
                current_app.permanent_session_lifetime = timedelta(hours=4)

                session['user_id'] = user.id
                session['username'] = user.name
                session['usermobile'] = getattr(user, "mobil", "")
                return redirect(url_for('checkin.checkin'))
            else:
                print("❌ Fel lösenord för användare:", user.name)
        else:
            print("❌ Ingen användare hittades med namn:", namn)

        error = "Fel namn eller lösenord."
        return render_template('login.html', error=error), 401

    return render_template('login.html', error=error)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))




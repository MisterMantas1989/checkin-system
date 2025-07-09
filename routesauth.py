from flask import Blueprint, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash
from models import User

auth_bp = Blueprint("auth", __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        namn = request.form.get('namn')
        lösenord = request.form.get('lösenord')
        print("Inloggningstest:", namn, lösenord)
        try:
            user = User.query.filter_by(name=namn).first()
        except Exception as e:
            print("❌ Fel vid databasfråga:", e)
            error = "Serverfel. Kontakta administratör."
            return render_template('login.html', error=error), 500

        if user:
            print("Användare finns. Hash i databasen:", user.password_hash)
            if check_password_hash(user.password_hash, lösenord):
                print("Hash-VERIFIERING OK!")
                session['user_id'] = user.id
                session['username'] = user.name
                session['usermobile'] = getattr(user, "mobil", "")
                return redirect(url_for('checkin.checkin'))
            else:
                print("Hash-VERIFIERING MISSLYCKADES!")
        else:
            print("Ingen användare hittades!")

        error = "Fel namn eller lösenord."
    return render_template('login.html', error=error)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))




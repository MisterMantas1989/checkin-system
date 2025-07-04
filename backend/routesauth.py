from flask import Blueprint, request, render_template, redirect, url_for, session, flash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def home():
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        namn = request.form.get('namn', '').strip()
        mobil = request.form.get('mobil', '').strip().zfill(10)
        if not (namn and mobil.isdigit() and len(mobil) == 10):
            return render_template('login.html', error="Ange både namn och giltigt 10-siffrigt mobilnummer")
        session['username'] = namn
        session['usermobile'] = mobil
        return redirect(url_for('checkin.checkin'))
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

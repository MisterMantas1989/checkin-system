from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import SQLALCHEMY_DATABASE_URI
from models import db
from routesauth import auth_bp
from routescheckin import checkin_bp
from routeshistory import history_bp
from routesadmin import admin_bp
from routeschat import chat_bp


app = Flask(__name__)
app.secret_key = 'MantasVanagas1989'
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Registrera Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(checkin_bp)
app.register_blueprint(history_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(chat_bp)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)

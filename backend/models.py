from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime
from datetime import datetime, timezone
import pytz

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    token = db.Column(db.String, unique=True)
    push_token = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<User {self.name}>"


class Checkin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100), nullable=False)
    checkin_time = db.Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    checkin_address = db.Column(db.String(255))
    checkout_time = db.Column(DateTime(timezone=True), nullable=True)
    checkout_address = db.Column(db.String(255))
    work_time_minutes = db.Column(db.Integer)
    total_work_today = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        sweden_tz = pytz.timezone("Europe/Stockholm")
        return {
            "ID": self.id,
            "Namn": self.user,
            "Checkin-tid": self.checkin_time.astimezone(sweden_tz).strftime("%Y-%m-%d %H:%M:%S") if self.checkin_time else None,
            "Checkin-adress": self.checkin_address,
            "Checkout-tid": self.checkout_time.astimezone(sweden_tz).strftime("%Y-%m-%d %H:%M:%S") if self.checkout_time else None,
            "Checkout-adress": self.checkout_address,
            "Total tid (minuter)": self.work_time_minutes,
            "Aktiv": self.is_active,
        }


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100))
    message = db.Column(db.Text)
    timestamp = db.Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        sweden_tz = pytz.timezone("Europe/Stockholm")
        return {
            "id": self.id,
            "user": self.user,
            "message": self.message,
            "timestamp": self.timestamp.astimezone(sweden_tz).strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else None
        }


class Schema(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    namn = db.Column(db.String(100))
    datum = db.Column(db.String(20))
    starttid = db.Column(db.String(20))
    sluttid = db.Column(db.String(20))
    adress = db.Column(db.String(255))
    kommentar = db.Column(db.String(255))

    def to_dict(self):
        return {
            "Namn": self.namn,
            "Datum": self.datum,
            "Starttid": self.starttid,
            "Sluttid": self.sluttid,
            "Adress": self.adress,
            "Kommentar": self.kommentar
        }






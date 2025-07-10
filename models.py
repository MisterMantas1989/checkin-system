from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime
from datetime import datetime

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
    user = db.Column(db.String(100))
    checkin_time = db.Column(db.String(50))
    checkin_address = db.Column(db.String(255))
    checkout_time = db.Column(db.String(50))
    checkout_address = db.Column(db.String(255))
    work_time_minutes = db.Column(db.Integer)
    total_work_today = db.Column(db.Integer) 

    def to_dict(self):
        return {
            "ID": self.id,
            "Namn": self.user,
            "Checkin-tid": self.checkin_time,
            "Checkin-adress": self.checkin_address,
            "Checkout-tid": self.checkout_time,
            "Checkout-adress": self.checkout_address,
            "Total tid (minuter)": self.work_time_minutes,
        }

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100))
    message = db.Column(db.Text)
    timestamp = db.Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user": self.user,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
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





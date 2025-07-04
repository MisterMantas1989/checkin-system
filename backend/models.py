from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Checkin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100))
    mobil = db.Column(db.String(20))
    checkin_time = db.Column(db.String(50))
    checkin_address = db.Column(db.String(255))
    checkout_time = db.Column(db.String(50))
    checkout_address = db.Column(db.String(255))
    work_time_minutes = db.Column(db.Integer)

    def to_dict(self):
        return {
            'ID': self.id,
            'Namn': self.user,
            'Mobil': self.mobil,
            'Checkin': self.checkin_time,
            'Checkin-adress': self.checkin_address,
            'Checkout': self.checkout_time,
            'Checkout-adress': self.checkout_address,
            'Arbetad tid (minuter)': self.work_time_minutes
        }

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100))
    message = db.Column(db.Text)
    timestamp = db.Column(db.String(50))

class Schema(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    namn = db.Column(db.String(100))
    datum = db.Column(db.String(20))
    starttid = db.Column(db.String(20))
    sluttid = db.Column(db.String(20))
    adress = db.Column(db.String(255))      
    kommentar = db.Column(db.String(255))


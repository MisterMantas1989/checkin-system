import requests
from backend.models import User

def send_push_to_all_users(title, body):
    users = User.query.filter(User.push_token.isnot(None)).all()
    for user in users:
        payload = {
            "to": user.push_token,
            "sound": "default",
            "title": title,
            "body": body,
        }
        r = requests.post("https://exp.host/--/api/v2/push/send", json=payload)
        print(f"Notis till {user.name}: {r.status_code}")

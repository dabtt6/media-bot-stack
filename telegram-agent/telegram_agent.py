from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

BOT_TOKEN = "8250674343:AAEoMCQJ9MoLMyQxgQmLqZhXvuzZRx7kyPY"
CHAT_ID = "-1003877872912"

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text
    }
    requests.post(url, data=data)

@app.route("/notify", methods=["POST"])
def notify():
    data = request.json
    message = data.get("message")

    if message:
        send_message(message)
        return jsonify({"status": "sent"})
    return jsonify({"status": "no message"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)

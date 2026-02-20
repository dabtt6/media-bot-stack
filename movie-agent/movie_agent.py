from flask import Flask, jsonify
import os

BASE_PATH = "/data"

app = Flask(__name__)

def get_all_codes():
    codes = set()
    for root, dirs, files in os.walk(BASE_PATH):
        for name in dirs:
            if "-" in name:
                codes.add(name.upper())
    return list(codes)

@app.route("/has_code/<code>")
def has_code(code):
    code = code.upper()
    for root, dirs, files in os.walk(BASE_PATH):
        for name in dirs:
            if code in name.upper():
                return jsonify({"exists": True})
    return jsonify({"exists": False})

@app.route("/all_codes")
def all_codes():
    return jsonify(get_all_codes())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)

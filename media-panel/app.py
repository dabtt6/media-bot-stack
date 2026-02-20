from flask import Flask, render_template, request, redirect
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

DB = "/app/data/crawler_master_full.db"
LOG_FILE = "/app/data/system.log"


def get_conn():
    return sqlite3.connect(DB)


@app.route("/")
def index():

    # Load logs
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = f.readlines()[-200:]

    # Load actors
    conn = get_conn()
    actors = conn.execute(
        "SELECT id,name,source,url FROM actors ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return render_template("index.html", logs=logs[::-1], actors=actors)


@app.route("/add_actor", methods=["POST"])
def add_actor():

    name = request.form.get("name")
    source = request.form.get("source")
    url = request.form.get("url")

    if name and source and url:
        conn = get_conn()
        conn.execute(
            "INSERT INTO actors(name,source,url,created_at) VALUES(?,?,?,?)",
            (name, source, url, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)

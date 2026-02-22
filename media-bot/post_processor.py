# -*- coding: utf-8 -*-

import sqlite3
import requests
import os
import time
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "data", "crawler_master_full.db")

QBIT_URL = os.getenv("QBIT_URL")
QBIT_USER = os.getenv("QBIT_USER")
QBIT_PASS = os.getenv("QBIT_PASS")

MOVIE_ROOT = "/data/movies"
CHECK_INTERVAL = 15

SESSION = requests.Session()


# =========================
# LOGGER
# =========================
def log(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{now} | TOOL6 | {msg}", flush=True)


# =========================
# DB CONNECT
# =========================
def get_conn():
    return sqlite3.connect(DB)


# =========================
# LOGIN
# =========================
def login():
    while True:
        try:
            r = SESSION.post(
                QBIT_URL + "/api/v2/auth/login",
                data={"username": QBIT_USER, "password": QBIT_PASS},
                timeout=10
            )
            if "Ok" in r.text:
                log("Connected qBit")
                return
        except:
            pass

        log("Waiting qBit...")
        time.sleep(5)


# =========================
# GET COMPLETED
# =========================
def get_completed():
    try:
        r = SESSION.get(QBIT_URL + "/api/v2/torrents/info", timeout=15)
        torrents = r.json()
        return [t for t in torrents if t["progress"] == 1.0]
    except:
        return []


# =========================
# MOVE + RENAME
# =========================
def process_completed():

    completed = get_completed()
    if not completed:
        return

    conn = get_conn()
    c = conn.cursor()

    for t in completed:

        hash_value = t["hash"]
        name = t["name"]
        save_path = t["save_path"]

        row = c.execute("""
            SELECT id, code, moved_at
            FROM queuedqbit
            WHERE hash=?
        """, (hash_value,)).fetchone()

        if not row:
            continue

        row_id, code, moved_at = row

        if moved_at:
            continue

        source_path = os.path.join(save_path, name)

        if not os.path.exists(source_path):
            continue

        os.makedirs(MOVIE_ROOT, exist_ok=True)

        # N?u torrent là folder
        if os.path.isdir(source_path):

            for root, dirs, files in os.walk(source_path):
                for f in files:
                    if f.lower().endswith((".mp4", ".mkv", ".avi")):
                        src_file = os.path.join(root, f)
                        ext = os.path.splitext(f)[1]
                        dst_file = os.path.join(MOVIE_ROOT, f"{code}{ext}")

                        shutil.move(src_file, dst_file)
                        log(f"MOVED {code}{ext}")

            shutil.rmtree(source_path, ignore_errors=True)

        else:
            # Single file torrent
            ext = os.path.splitext(name)[1]
            dst_file = os.path.join(MOVIE_ROOT, f"{code}{ext}")

            shutil.move(source_path, dst_file)
            log(f"MOVED {code}{ext}")

        c.execute("""
            UPDATE queuedqbit
            SET moved_at=?, status='moved'
            WHERE id=?
        """, (datetime.now().isoformat(), row_id))

        conn.commit()

    conn.close()


# =========================
# MAIN LOOP
# =========================
def main():

    log("Started")

    login()

    while True:
        try:
            process_completed()
        except Exception as e:
            log(f"ERROR: {str(e)}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
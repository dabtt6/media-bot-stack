# -*- coding: utf-8 -*-

import sqlite3
import requests
import os
import shutil
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "data", "crawler_master_full.db")

QBIT_URL = os.getenv("QBIT_URL")
QBIT_USER = os.getenv("QBIT_USER")
QBIT_PASS = os.getenv("QBIT_PASS")

DEST_DIR = "/data/movies"
VIDEO_EXT = (".mkv", ".mp4", ".avi", ".mov")

SESSION = requests.Session()


# ================= DB =================
def get_conn():
    return sqlite3.connect(DB)


# ================= LOGIN =================
def login():
    while True:
        try:
            r = SESSION.post(
                QBIT_URL + "/api/v2/auth/login",
                data={"username": QBIT_USER, "password": QBIT_PASS},
                timeout=10
            )
            if r.text == "Ok.":
                print("TOOL6 | qBit connected")
                return
        except:
            pass

        print("TOOL6 | Waiting qBit...")
        time.sleep(5)


# ================= FIND BIGGEST VIDEO =================
def find_video(folder):
    biggest = None
    biggest_size = 0

    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(VIDEO_EXT):
                path = os.path.join(root, f)
                size = os.path.getsize(path)
                if size > biggest_size:
                    biggest = path
                    biggest_size = size

    return biggest


# ================= MAIN PROCESS =================
def process_completed():

    conn = get_conn()
    c = conn.cursor()

    rows = c.execute("""
        SELECT id, code, hash, save_path
        FROM queuedqbit
        WHERE status='completed'
          AND moved_at IS NULL
          AND hash IS NOT NULL
    """).fetchall()

    conn.close()

    if not rows:
        return

    torrents = SESSION.get(
        QBIT_URL + "/api/v2/torrents/info",
        timeout=20
    ).json()

    torrent_map = {t["hash"]: t for t in torrents}

    for row_id, code, hash_value, save_path in rows:

        t = torrent_map.get(hash_value)
        if not t:
            continue

        folder = os.path.join(save_path, t["name"])

        if not os.path.exists(folder):
            continue

        video = find_video(folder)
        if not video:
            print(f"TOOL6 | No video found for {code}")
            continue

        ext = os.path.splitext(video)[1]
        new_name = f"{code.upper()}{ext}"
        dest_file = os.path.join(DEST_DIR, new_name)

        if os.path.exists(dest_file):
            print(f"TOOL6 | File exists skip {new_name}")
            continue

        try:
            shutil.move(video, dest_file)
            print(f"TOOL6 | Moved {code} → {dest_file}")

            conn = get_conn()
            conn.execute("""
                UPDATE queuedqbit
                SET moved_at=?
                WHERE id=?
            """, (datetime.now().isoformat(), row_id))
            conn.commit()
            conn.close()

            # Optional: remove torrent from qbit
            SESSION.post(
                QBIT_URL + "/api/v2/torrents/delete",
                data={"hashes": hash_value, "deleteFiles": "false"}
            )

        except Exception as e:
            print(f"TOOL6 | Move failed {code} | {e}")


# ================= LOOP =================
def main():
    login()

    while True:
        try:
            process_completed()
        except Exception as e:
            print("TOOL6 ERROR:", e)
            login()

        time.sleep(10)


if __name__ == "__main__":
    main()

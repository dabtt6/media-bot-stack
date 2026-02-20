# -*- coding: utf-8 -*-

import sqlite3
import requests
import time
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "data", "crawler_master_full.db")

QBIT_URL = os.getenv("QBIT_URL")
QBIT_USER = os.getenv("QBIT_USER")
QBIT_PASS = os.getenv("QBIT_PASS")

MAX_RETRY = 3

SESSION = requests.Session()


def log(msg):
    print(f"[TOOL4] {datetime.now().isoformat()} - {msg}", flush=True)


# ===============================
# LOGIN
# ===============================
def login():
    while True:
        try:
            r = SESSION.post(
                QBIT_URL + "/api/v2/auth/login",
                data={"username": QBIT_USER, "password": QBIT_PASS},
                timeout=10
            )
            if r.text == "Ok.":
                log("qBit ready")
                return
        except Exception:
            pass

        log("Waiting for qBit...")
        time.sleep(5)


# ===============================
# DOWNLOAD
# ===============================
def download_torrent(url):
    r = requests.get(url, timeout=(10, 60))
    if r.status_code != 200:
        raise Exception("Download failed")
    return r.content


# ===============================
# ADD
# ===============================
def add_torrent(data, save_path):

    os.makedirs(save_path, exist_ok=True)

    files = {"torrents": ("file.torrent", data)}
    payload = {
        "savepath": save_path,
        "autoTMM": False
    }

    r = SESSION.post(
        QBIT_URL + "/api/v2/torrents/add",
        files=files,
        data=payload,
        timeout=(10, 60)
    )

    if r.status_code != 200:
        raise Exception("Add failed")


# ===============================
# PROCESS
# ===============================
def process_cycle():

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    rows = c.execute("""
        SELECT id, code, torrent_url, actor_name, retry_count
        FROM queuedqbit
        WHERE status='new'
           OR (status='error' AND COALESCE(retry_count,0) < ?)
        ORDER BY id ASC
        LIMIT 2
    """, (MAX_RETRY,)).fetchall()

    if not rows:
        conn.close()
        return

    for row_id, code, url, actor, retry_count in rows:

        log(f"Processing {code}")

        try:
            c.execute("UPDATE queuedqbit SET status='adding' WHERE id=?", (row_id,))
            conn.commit()

            torrent_data = download_torrent(url)

            save_path = f"/data/downloads/{actor}"
            add_torrent(torrent_data, save_path)

            c.execute("""
                UPDATE queuedqbit
                SET status='added',
                    added_at=?,
                    last_try_at=?,
                    retry_count=0
                WHERE id=?
            """, (datetime.now().isoformat(),
                  datetime.now().isoformat(),
                  row_id))

            conn.commit()
            log(f"Added {code}")

        except Exception as e:

            log(f"Error {code}: {e}")

            c.execute("""
                UPDATE queuedqbit
                SET status='error',
                    retry_count=COALESCE(retry_count,0)+1,
                    last_try_at=?
                WHERE id=?
            """, (datetime.now().isoformat(), row_id))

            conn.commit()

    conn.close()


# ===============================
# MAIN
# ===============================
def main():

    log("TOOL 4 STARTED")

    login()

    while True:
        try:
            process_cycle()
        except Exception as e:
            log(f"Worker crash: {e}")
            login()

        time.sleep(5)


if __name__ == "__main__":
    main()
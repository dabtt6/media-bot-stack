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

SESSION = requests.Session()

def log(msg):
    print(f"[TOOL4] {datetime.now().isoformat()} - {msg}", flush=True)


# ===============================
# WAIT FOR QBIT
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
                return True

        except Exception:
            pass

        log("Waiting for qBit...")
        time.sleep(5)


# ===============================
# DOWNLOAD TORRENT FILE
# ===============================
def download_torrent(url):
    r = requests.get(url, timeout=30)
    if r.status_code != 200:
        raise Exception("Download failed")
    return r.content


# ===============================
# ADD TO QBIT
# ===============================
def add_torrent(data, save_path):
    files = {"torrents": ("file.torrent", data)}
    payload = {
        "savepath": save_path,
        "autoTMM": False
    }

    r = SESSION.post(
        QBIT_URL + "/api/v2/torrents/add",
        files=files,
        data=payload,
        timeout=30
    )

    if r.status_code != 200:
        raise Exception("Add failed")


# ===============================
# PROCESS ONE BATCH
# ===============================
def process_cycle():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    rows = c.execute("""
        SELECT id, code, torrent_url, actor_name
        FROM queuedqbit
        WHERE status='new'
        ORDER BY id ASC
        LIMIT 3
    """).fetchall()

    if not rows:
        conn.close()
        return

    for row_id, code, url, actor in rows:
        log(f"Processing {code}")

        try:
            c.execute("UPDATE queuedqbit SET status='adding' WHERE id=?", (row_id,))
            conn.commit()

            torrent_data = download_torrent(url)
            save_path = f"/data/downloads/{actor}"

            add_torrent(torrent_data, save_path)

            now = datetime.now().isoformat()

            c.execute("""
                UPDATE queuedqbit
                SET status='added',
                    added_at=?
                WHERE id=?
            """, (now, row_id))

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
# MAIN LOOP
# ===============================
def main():
    log("TOOL 4 - ADD WORKER STARTED")

    login()

    while True:
        try:
            process_cycle()
        except Exception as e:
            log(f"Worker crash: {e}")
            login()

        time.sleep(3)


if __name__ == "__main__":
    main()
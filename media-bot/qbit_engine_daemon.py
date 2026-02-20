# -*- coding: utf-8 -*-

import sqlite3
import requests
import os
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "data", "crawler_master_full.db")

QBIT_URL = os.environ.get("QBIT_URL", "http://qbittorrent:8080")
USERNAME = os.environ.get("QBIT_USER", "admin")
PASSWORD = os.environ.get("QBIT_PASS", "111111")

MAX_RETRY = 3
RETRY_DELAY_MINUTES = 5
ADDING_TIMEOUT_MINUTES = 10

SESSION = requests.Session()

# =========================
# LOGIN WITH RETRY
# =========================
def login_with_retry():
    while True:
        try:
            r = SESSION.post(
                QBIT_URL + "/api/v2/auth/login",
                data={"username": USERNAME, "password": PASSWORD},
                timeout=10
            )
            if r.text == "Ok.":
                print("? qBit ready")
                return
        except:
            pass
        print("? Waiting for qBit...")
        time.sleep(5)

# =========================
# CHECK EXISTS IN QBIT
# =========================
def exists_in_qbit(code):
    try:
        r = SESSION.get(QBIT_URL + "/api/v2/torrents/info", timeout=10)
        if r.status_code != 200:
            return False
        torrents = r.json()
        for t in torrents:
            if code.lower() in t.get("name", "").lower():
                return True
        return False
    except:
        return False

# =========================
# DOWNLOAD
# =========================
def download_torrent(url):
    r = requests.get(url, timeout=30)
    if r.status_code != 200:
        raise Exception("Download failed")
    return r.content

# =========================
# ADD TORRENT
# =========================
def add_torrent(data, save_path):
    files = {"torrents": ("file.torrent", data)}
    payload = {"savepath": save_path, "autoTMM": False}

    r = SESSION.post(
        QBIT_URL + "/api/v2/torrents/add",
        files=files,
        data=payload,
        timeout=30
    )

    if r.status_code != 200:
        raise Exception("Add failed")

# =========================
# RECOVER STUCK ADDING
# =========================
def recover_stuck():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        UPDATE queuedqbit
        SET status='new'
        WHERE status='adding'
        AND datetime(last_try_at) < datetime('now', ?)
    """, (f'-{ADDING_TIMEOUT_MINUTES} minutes',))

    recovered = c.rowcount
    conn.commit()
    conn.close()

    if recovered:
        print("? Recovered stuck adding:", recovered)

# =========================
# WORKER LOOP
# =========================
def worker_loop():

    login_with_retry()
    print("?? Tool 4 worker started")

    recover_stuck()

    while True:

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        row = c.execute("""
            SELECT id, code, torrent_url, actor_name, retry_count, last_try_at
            FROM queuedqbit
            WHERE 
                status='new'
                OR (
                    status='error'
                    AND retry_count < ?
                    AND datetime(last_try_at) < datetime('now', ?)
                )
            ORDER BY id ASC
            LIMIT 1
        """, (MAX_RETRY, f'-{RETRY_DELAY_MINUTES} minutes')).fetchone()

        if not row:
            conn.close()
            time.sleep(5)
            continue

        row_id, code, url, actor, retry, last_try = row

        # MARK ADDING
        c.execute("""
            UPDATE queuedqbit
            SET status='adding',
                last_try_at=?
            WHERE id=? AND (status='new' OR status='error')
        """, (datetime.now().isoformat(), row_id))

        if c.rowcount == 0:
            conn.close()
            continue

        conn.commit()
        print("? ADDING:", code)

        try:

            # CHECK EXISTS
            if exists_in_qbit(code):
                c.execute("""
                    UPDATE queuedqbit
                    SET status='added',
                        retry_count=?
                    WHERE id=?
                """, (retry+1, row_id))
                conn.commit()
                print("? Already exists:", code)
                conn.close()
                continue

            torrent_data = download_torrent(url)
            save_path = f"/data/downloads/{actor}"
            add_torrent(torrent_data, save_path)

            c.execute("""
                UPDATE queuedqbit
                SET status='added',
                    retry_count=?
                WHERE id=?
            """, (retry+1, row_id))

            conn.commit()
            print("? Added:", code)

        except Exception as e:

            if retry + 1 >= MAX_RETRY:
                new_status = "failed"
            else:
                new_status = "error"

            c.execute("""
                UPDATE queuedqbit
                SET status=?,
                    retry_count=?,
                    last_try_at=?
                WHERE id=?
            """, (new_status, retry+1, datetime.now().isoformat(), row_id))

            conn.commit()
            print("? Error:", code, "?", new_status, "|", e)

        conn.close()
        time.sleep(2)

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    worker_loop()
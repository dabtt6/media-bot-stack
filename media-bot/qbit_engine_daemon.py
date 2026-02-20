# -*- coding: utf-8 -*-

import sqlite3
import requests
import os
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "data", "crawler_master_full.db")

QBIT_URL = os.environ.get("QBIT_URL")
USERNAME = os.environ.get("QBIT_USER")
PASSWORD = os.environ.get("QBIT_PASS")

SESSION = requests.Session()

MAX_RETRY = 3

def login():
    r = SESSION.post(
        QBIT_URL + "/api/v2/auth/login",
        data={"username": USERNAME, "password": PASSWORD}
    )
    return r.text == "Ok."

def process_one():

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    row = c.execute("""
        SELECT id, code, torrent_url, retry_count
        FROM queuedqbit
        WHERE status='new'
        LIMIT 1
    """).fetchone()

    if not row:
        conn.close()
        return False

    row_id, code, url, retry = row

    c.execute("UPDATE queuedqbit SET status='adding' WHERE id=?", (row_id,))
    conn.commit()

    try:
        torrent_data = requests.get(url, timeout=30).content

        files = {'torrents': ('file.torrent', torrent_data)}
        r = SESSION.post(QBIT_URL + "/api/v2/torrents/add", files=files)

        if r.status_code != 200:
            raise Exception("Add failed")

        c.execute("""
            UPDATE queuedqbit
            SET status='added'
            WHERE id=?
        """,(row_id,))

        print("Added:", code)

    except Exception as e:

        retry += 1

        new_status = "failed" if retry >= MAX_RETRY else "new"

        c.execute("""
            UPDATE queuedqbit
            SET status=?, retry_count=?
            WHERE id=?
        """,(new_status, retry, row_id))

        print("Error:", code, e)

    conn.commit()
    conn.close()
    return True

def main():

    print("? TOOL 4 - ADD WORKER")

    while True:

        if not login():
            print("Login fail")
            time.sleep(30)
            continue

        processed = process_one()

        if not processed:
            time.sleep(10)

if __name__ == "__main__":
    main()
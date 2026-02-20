import requests
import sqlite3
import os
import time
from logger_core import log

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "data", "crawler_master_full.db")

QBIT_URL = os.getenv("QBIT_URL")
QBIT_USER = os.getenv("QBIT_USER")
QBIT_PASS = os.getenv("QBIT_PASS")

SESSION = requests.Session()

def login():
    while True:
        try:
            r = SESSION.post(
                QBIT_URL + "/api/v2/auth/login",
                data={"username": QBIT_USER, "password": QBIT_PASS},
                timeout=10
            )
            if r.text == "Ok.":
                log("TOOL4", "RUNNING", "qBit login OK")
                return
        except:
            log("TOOL4", "ERROR", "Login failed")

        time.sleep(5)

def main():
    log("TOOL4", "START", "Add worker started")
    login()

    while True:
        conn = sqlite3.connect(DB)
        c = conn.cursor()

        row = c.execute("""
            SELECT id, code, torrent_url FROM queuedqbit
            WHERE status='new'
            LIMIT 1
        """).fetchone()

        if not row:
            log("TOOL4", "IDLE", "No new torrents")
            conn.close()
            time.sleep(20)
            continue

        row_id, code, url = row

        try:
            SESSION.post(
                QBIT_URL + "/api/v2/torrents/add",
                data={"urls": url}
            )

            c.execute("UPDATE queuedqbit SET status='added' WHERE id=?", (row_id,))
            conn.commit()

            log("TOOL4", "RUNNING", f"Added torrent: {code}")

        except Exception as e:
            log("TOOL4", "ERROR", str(e))

        conn.close()
        time.sleep(50)

if __name__ == "__main__":
    main()
import sqlite3
import requests
import time
import os
from datetime import datetime

DB = "/docker/media-stack/data/crawler/crawler_master_full.db"

QBIT_URL = "http://10.0.0.3:8080"
USERNAME = "admin"
PASSWORD = "111111"

SESSION = requests.Session()

def login():
    r = SESSION.post(
        QBIT_URL + "/api/v2/auth/login",
        data={"username": USERNAME, "password": PASSWORD}
    )
    if r.text != "Ok.":
        raise Exception("Login failed")
    print("✅ qBit Login OK")

def download_torrent(url):
    r = requests.get(url, timeout=30)
    if r.status_code != 200:
        raise Exception("Download failed")
    return r.content

def add_torrent(data, save_path):
    files = {'torrents': ('file.torrent', data)}
    data = {
        'savepath': save_path,
        'autoTMM': False
    }
    r = SESSION.post(QBIT_URL + "/api/v2/torrents/add", files=files, data=data)
    if r.status_code != 200:
        raise Exception("Add failed")

def process_cycle():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Retry lỗi trước
    rows = c.execute("""
        SELECT id, code, torrent_url, actor_name, retry_count
        FROM queuedqbit
        WHERE status='error'
        ORDER BY retry_count ASC
        LIMIT 10
    """).fetchall()

    if not rows:
        rows = c.execute("""
            SELECT id, code, torrent_url, actor_name, retry_count
            FROM queuedqbit
            WHERE status='queue_add'
            LIMIT 10
        """).fetchall()

    if not rows:
        print("🟢 Nothing to process")
        conn.close()
        return

    for row in rows:
        row_id, code, url, actor, retry = row
        print("⬇ Processing:", code)

        try:
            torrent_data = download_torrent(url)

            save_path = f"/data/downloads/{actor}"
            add_torrent(torrent_data, save_path)

            c.execute("""
                UPDATE queuedqbit
                SET status='added',
                    last_try_at=?,
                    retry_count=?
                WHERE id=?
            """, (datetime.now().isoformat(), retry+1, row_id))

            print("🚀 Added:", code)

        except Exception as e:
            print("❌ Error:", code, e)

            c.execute("""
                UPDATE queuedqbit
                SET status='error',
                    last_try_at=?,
                    retry_count=?
                WHERE id=?
            """, (datetime.now().isoformat(), retry+1, row_id))

        conn.commit()

    conn.close()

def main():
    print("🟢 TOOL 4 – DAEMON RETRY MODE")
    login()

    while True:
        process_cycle()
        print("⏳ Sleeping 30s...")
        time.sleep(30)

if __name__ == "__main__":
    main()

import sqlite3
import requests
import os
from datetime import datetime

DB = "/docker/media-stack/data/crawler/crawler_master_full.db"

QBIT_HOST = "http://10.0.0.3:8080"
QBIT_USER = "admin"
QBIT_PASS = "111111"

session = requests.Session()

# ==============================
# LOGIN QB
# ==============================
def qbit_login():
    r = session.post(
        f"{QBIT_HOST}/api/v2/auth/login",
        data={"username": QBIT_USER, "password": QBIT_PASS},
        timeout=15
    )
    if r.text != "Ok.":
        raise Exception("qBit login failed")
    print("✅ qBit Login OK")

# ==============================
# ADD TORRENT MEMORY
# ==============================
def add_torrent_memory(torrent_url, save_path):
    try:
        # download torrent to memory
        torrent_resp = session.get(torrent_url, timeout=30)
        torrent_resp.raise_for_status()

        files = {
            "torrents": ("file.torrent", torrent_resp.content)
        }

        data = {
            "savepath": save_path,
            "autoTMM": "false",
            "paused": "false"
        }

        r = session.post(
            f"{QBIT_HOST}/api/v2/torrents/add",
            files=files,
            data=data,
            timeout=30
        )

        if r.status_code == 200:
            return True
        return False

    except Exception as e:
        print("❌ Add error:", e)
        return False

# ==============================
# MAIN
# ==============================
def main():
    print("🟢 TOOL 4 – QB MEMORY PRO")
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    qbit_login()

    rows = c.execute("""
        SELECT id, actor_name, code, torrent_url
        FROM queuedqbit
        WHERE status='queue_add'
    """).fetchall()

    print("To add:", len(rows))

    for row in rows:
        row_id, actor, code, torrent_url = row
        save_path = f"/data/downloads/{actor_name}"

        print(f"➡ Adding: {code} ({actor})")

        ok = add_torrent_memory(torrent_url, save_path)

        if ok:
            c.execute("""
                UPDATE queuedqbit
                SET status='added'
                WHERE id=?
            """, (row_id,))
            print("   ✔ Added")
        else:
            c.execute("""
                UPDATE queuedqbit
                SET status='add_error'
                WHERE id=?
            """, (row_id,))
            print("   ✘ Failed")

        conn.commit()

    conn.close()
    print("🏁 DONE")

if __name__ == "__main__":
    main()

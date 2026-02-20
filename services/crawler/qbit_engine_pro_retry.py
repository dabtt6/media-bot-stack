import sqlite3
import requests
import os
import time
from datetime import datetime

DB = "/docker/media-stack/data/crawler/crawler_master_full.db"

QBIT_URL = "http://10.0.0.3:8080"
QBIT_USER = "admin"
QBIT_PASS = "111111"

MAX_RETRY = 5
HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# QB LOGIN
# =========================
def qbit_login():
    s = requests.Session()
    r = s.post(f"{QBIT_URL}/api/v2/auth/login",
               data={"username":QBIT_USER,"password":QBIT_PASS})
    if r.text.strip() == "Ok.":
        return s
    return None

# =========================
# MAIN
# =========================
def main():
    print("🟢 TOOL 4 – QB RETRY PRO")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    q = qbit_login()
    if not q:
        print("❌ qBit login fail")
        return

    print("✅ qBit Login OK")

    rows = c.execute("""
        SELECT id, actor_name, code, torrent_url, retry_count
        FROM queuedqbit
        WHERE status='queue_add'
    """).fetchall()

    print("To process:", len(rows))

    for row in rows:
        qid, actor_name, code, torrent_url, retry = row

        if retry >= MAX_RETRY:
            print("⚠ Max retry reached:", code)
            c.execute("UPDATE queuedqbit SET status='failed' WHERE id=?", (qid,))
            conn.commit()
            continue

        try:
            print("⬇ Downloading:", code)

            r = requests.get(torrent_url,
                             headers=HEADERS,
                             timeout=60)

            if r.status_code != 200:
                raise Exception(f"HTTP {r.status_code}")

            tmp_file = f"/tmp/{code}.torrent"
            with open(tmp_file, "wb") as f:
                f.write(r.content)

            save_path = f"/data/downloads/{actor_name}"
            os.makedirs(save_path, exist_ok=True)

            print("🚀 Adding to qBit:", code)

            with open(tmp_file, "rb") as f:
                q.post(f"{QBIT_URL}/api/v2/torrents/add",
                       files={"torrents": f},
                       data={"savepath": save_path})

            os.remove(tmp_file)

            c.execute("""
                UPDATE queuedqbit
                SET status='added',
                    last_try_at=?,
                    last_error=NULL
                WHERE id=?
            """, (datetime.now().isoformat(), qid))
            conn.commit()

            print("✅ Added:", code)

        except Exception as e:
            err = str(e)[:300]
            print("❌ Error:", code, err)

            c.execute("""
                UPDATE queuedqbit
                SET retry_count = retry_count + 1,
                    last_error = ?,
                    last_try_at = ?
                WHERE id=?
            """, (err, datetime.now().isoformat(), qid))
            conn.commit()

            # exponential backoff
            sleep_time = 5 * (retry + 1)
            print("⏳ Sleep", sleep_time, "seconds")
            time.sleep(sleep_time)

    conn.close()
    print("🏁 DONE")

if __name__ == "__main__":
    main()

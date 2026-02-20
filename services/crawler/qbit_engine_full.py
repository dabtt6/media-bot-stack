import sqlite3
import requests
import os
import tempfile
from datetime import datetime

# =========================
# CONFIG
# =========================
DB = '/docker/media-stack/data/crawler/crawler_master_full.db'

QBIT_URL = "http://10.0.0.3:8080"
QBIT_USER = "admin"
QBIT_PASS = "111111"

DOWNLOAD_TIMEOUT = 60

# =========================
# INIT
# =========================
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("🔵 QBittorrent Engine START")

# =========================
# LOGIN QB
# =========================
session = requests.Session()

login = session.post(
    QBIT_URL + "/api/v2/auth/login",
    data={"username": QBIT_USER, "password": QBIT_PASS},
    timeout=20
)

if login.text != "Ok.":
    print("❌ QB Login Failed")
    exit()

print("✅ QB Login OK")

# =========================
# GET QUEUED ITEMS
# =========================
rows = c.execute("""
SELECT id, actor_name, code, torrent_url
FROM queuedqbit
WHERE status='queue_add'
""").fetchall()

print("Items to add:", len(rows))

for row in rows:
    qid = row["id"]
    actor = row["actor_name"]
    code = row["code"]
    torrent_url = row["torrent_url"]

    print(f"\n➡ Adding: {code}")

    try:
        # -------------------------
        # Download torrent file
        # -------------------------
        r = requests.get(torrent_url, timeout=DOWNLOAD_TIMEOUT)
        if r.status_code != 200:
            raise Exception("Download failed")

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(r.content)
            tmp_path = tmp.name

        # -------------------------
        # Upload to qbit
        # -------------------------
        with open(tmp_path, 'rb') as f:
            files = {'torrents': f}
            data = {
                'category': actor,
                'savepath': f'/downloads/{actor}'
            }

            add = session.post(
                QBIT_URL + "/api/v2/torrents/add",
                files=files,
                data=data,
                timeout=30
            )

        os.remove(tmp_path)

        if add.status_code == 200:
            print("   ✅ Added to qbit")

            c.execute("""
            UPDATE queuedqbit
            SET status='added'
            WHERE id=?
            """,(qid,))
        else:
            print("   ❌ Add failed")
            c.execute("""
            UPDATE queuedqbit
            SET status='error'
            WHERE id=?
            """,(qid,))

        conn.commit()

    except Exception as e:
        print("   ❌ ERROR:", e)
        c.execute("""
        UPDATE queuedqbit
        SET status='error'
        WHERE id=?
        """,(qid,))
        conn.commit()

print("\n🎉 QB Engine DONE")

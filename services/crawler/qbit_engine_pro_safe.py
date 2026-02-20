import requests
import sqlite3
import os
import time

# =========================
# CONFIG
# =========================
DB = "/docker/media-stack/data/crawler/crawler_master_full.db"

QBIT_URL = "http://10.0.0.3:8080"
QBIT_USER = "admin"
QBIT_PASS = "111111"   # đổi nếu cần

DOWNLOAD_BASE = "/downloads"

# =========================
# LOGIN QB
# =========================
session = requests.Session()

def login_qbit():
    r = session.post(
        QBIT_URL + "/api/v2/auth/login",
        data={"username": QBIT_USER, "password": QBIT_PASS}
    )
    if r.text != "Ok.":
        raise Exception("Qbit login failed")
    print("✅ Qbit login OK")

# =========================
# ADD TORRENT
# =========================
def add_torrent(torrent_url, actor):
    try:
        save_path = os.path.join(DOWNLOAD_BASE, actor)

        # Auto create folder
        os.makedirs(save_path, exist_ok=True)

        # Try fix permission (ignore error if no sudo)
        try:
            os.chmod(save_path, 0o775)
        except:
            pass

        # Download torrent file
        tr = requests.get(torrent_url, timeout=30)
        if tr.status_code != 200:
            raise Exception("Torrent download failed")

        files = {
            "torrents": ("file.torrent", tr.content)
        }

        data = {
            "savepath": save_path,
            "category": actor,
            "autoTMM": "false"
        }

        r = session.post(
            QBIT_URL + "/api/v2/torrents/add",
            files=files,
            data=data
        )

        if r.status_code == 200:
            return True
        else:
            return False

    except Exception as e:
        print("❌ Add error:", e)
        return False

# =========================
# MAIN
# =========================
def main():
    login_qbit()

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    rows = c.execute("""
        SELECT id, actor_name, torrent_url
        FROM queuedqbit
        WHERE status='queue_add'
    """).fetchall()

    print("🟡 QUEUE TO ADD:", len(rows))

    for row in rows:
        id_, actor, torrent_url = row
        print("➡ Adding:", actor)

        ok = add_torrent(torrent_url, actor)

        if ok:
            c.execute("""
                UPDATE queuedqbit
                SET status='added'
                WHERE id=?
            """, (id_,))
            print("   ✔ Added")
        else:
            c.execute("""
                UPDATE queuedqbit
                SET status='error'
                WHERE id=?
            """, (id_,))
            print("   ✘ Failed")

        conn.commit()
        time.sleep(1)

    conn.close()
    print("\n✅ DONE")

if __name__ == "__main__":
    main()

import sqlite3
import requests
import os
import time

DB = "/docker/media-stack/data/crawler/crawler_master_full.db"

QBIT_URL  = "http://10.0.0.3:8080"
QBIT_USER = "admin"
QBIT_PASS = "111111"

DOWNLOAD_BASE = "/data/downloads"

# =========================
# LOGIN QB
# =========================
def qb_login():
    s = requests.Session()
    r = s.post(f"{QBIT_URL}/api/v2/auth/login",
               data={"username":QBIT_USER,"password":QBIT_PASS})
    if "Ok" not in r.text:
        print("❌ qBit login failed")
        return None
    print("✅ qBit Login OK")
    return s

# =========================
# ADD TORRENT MEMORY SAFE
# =========================
def add_torrent(session, torrent_url, save_path):
    try:
        r = session.get(torrent_url, timeout=30)
        if r.status_code != 200:
            print("❌ Download torrent file failed")
            return False

        files = {
            "torrents": ("file.torrent", r.content)
        }

        data = {
            "savepath": save_path,
            "autoTMM": "false"
        }

        resp = session.post(
            f"{QBIT_URL}/api/v2/torrents/add",
            files=files,
            data=data
        )

        if resp.status_code == 200:
            return True
        else:
            print("❌ qBit add error:", resp.text)
            return False

    except Exception as e:
        print("❌ Add exception:", e)
        return False


# =========================
# MAIN
# =========================
def main():
    print("🟢 TOOL 4 – QB MEMORY PRO FINAL CLEAN")

    session = qb_login()
    if not session:
        return

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    rows = c.execute("""
        SELECT id, code, actor_name, torrent_url
        FROM queuedqbit
        WHERE status='queue_add'
    """).fetchall()

    print("To add:", len(rows))

    for row in rows:
        qid, code, actor_name, torrent_url = row

        print(f"➡ Adding: {code}")

        save_path = f"{DOWNLOAD_BASE}/{actor_name}"

        # ensure folder exists inside mounted /data
        os.makedirs(save_path, exist_ok=True)

        # mark adding
        c.execute("UPDATE queuedqbit SET status='adding' WHERE id=?", (qid,))
        conn.commit()

        ok = add_torrent(session, torrent_url, save_path)

        if ok:
            print("   ✔ Added OK")
            c.execute("UPDATE queuedqbit SET status='added' WHERE id=?", (qid,))
        else:
            print("   ✘ Failed")
            c.execute("UPDATE queuedqbit SET status='error' WHERE id=?", (qid,))

        conn.commit()
        time.sleep(1)

    conn.close()
    print("🏁 DONE")

if __name__ == "__main__":
    main()

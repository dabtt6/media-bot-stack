import sqlite3
import requests

DB = '/docker/media-stack/data/crawler/crawler_master_test.db'
AGENT_URL = "http://127.0.0.1:5001"

conn = sqlite3.connect(DB)
c = conn.cursor()

print("\n🟡 CHECK QUEUE vs AGENT\n")

rows = c.execute("""
SELECT id, code FROM queuedqbit
WHERE status IS NULL OR status='queue'
""").fetchall()

print("Queue items:", len(rows))

need_add = 0
already_exist = 0

for row in rows:
    qid, code = row

    try:
        r = requests.get(f"{AGENT_URL}/has_code/{code}", timeout=5)
        exists = r.json().get("exists", False)
    except Exception as e:
        print("Agent error:", e)
        continue

    if exists:
        c.execute("UPDATE queuedqbit SET status='exists' WHERE id=?", (qid,))
        already_exist += 1
        print(f"✔ EXISTS  → {code}")
    else:
        c.execute("UPDATE queuedqbit SET status='ready_add' WHERE id=?", (qid,))
        need_add += 1
        print(f"➕ NEED ADD → {code}")

conn.commit()

print("\n==========================")
print("Already exist:", already_exist)
print("Need add:", need_add)
print("DONE.")

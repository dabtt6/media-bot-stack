import sqlite3
import requests
from datetime import datetime

DB = "/docker/media-stack/data/crawler/crawler_master_full.db"
AGENT_URL = "http://10.0.0.3:5001"

conn = sqlite3.connect(DB)
c = conn.cursor()

# =========================
# ENSURE TABLE AGENT
# =========================
c.execute("""
CREATE TABLE IF NOT EXISTS agent(
id INTEGER PRIMARY KEY AUTOINCREMENT,
code TEXT UNIQUE,
synced_at TEXT
)
""")

conn.commit()

# =========================
# SYNC AGENT CODES
# =========================
print("\n🟡 SYNC AGENT CODES")

try:
    r = requests.get(f"{AGENT_URL}/all_codes", timeout=20)
    agent_codes = r.json()
    print("Agent returned:", len(agent_codes), "codes")

    for code in agent_codes:
        c.execute("""
        INSERT OR IGNORE INTO agent(code, synced_at)
        VALUES (?,?)
        """,(code.upper(), datetime.now().isoformat()))

    conn.commit()

except Exception as e:
    print("Agent error:", e)
    conn.close()
    exit()

# =========================
# COMPARE WITH QUEUE
# =========================
print("\n🟢 COMPARE QUEUE WITH AGENT")

queue_rows = c.execute("""
SELECT id, code FROM queuedqbit
""").fetchall()

agent_set = set([row[0] for row in c.execute("SELECT code FROM agent").fetchall()])

ready = 0
skipped = 0

for qid, code in queue_rows:
    if code.upper() in agent_set:
        c.execute("""
        UPDATE queuedqbit
        SET status='skip_agent'
        WHERE id=?
        """,(qid,))
        skipped += 1
    else:
        c.execute("""
        UPDATE queuedqbit
        SET status='ready_add'
        WHERE id=?
        """,(qid,))
        ready += 1

conn.commit()

print("\n✅ READY TO ADD:", ready)
print("⛔ SKIPPED (already in agent):", skipped)

conn.close()

print("\nDONE.")

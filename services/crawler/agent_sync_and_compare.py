import sqlite3
import requests

DB = "/docker/media-stack/data/crawler/crawler_master_full.db"
AGENT_URL = "http://localhost:5001/all_codes"

conn = sqlite3.connect(DB)
c = conn.cursor()

print("\n?? SYNC AGENT CODES")

# 1?? L?Y CODE T? AGENT
try:
    r = requests.get(AGENT_URL, timeout=10)
    agent_codes = set(x.upper() for x in r.json())
    print("Agent returned:", len(agent_codes), "codes")
except Exception as e:
    print("Agent error:", e)
    agent_codes = set()

# 2?? L?Y CODE T? QUEUE
rows = c.execute("SELECT id, code FROM queuedqbit").fetchall()

exists_count = 0
queue_count = 0

for row_id, code in rows:
    if not code:
        continue

    code_upper = code.upper()

    if code_upper in agent_codes:
        c.execute(
            "UPDATE queuedqbit SET status='exists' WHERE id=?",
            (row_id,)
        )
        exists_count += 1
    else:
        c.execute(
            "UPDATE queuedqbit SET status='queue' WHERE id=?",
            (row_id,)
        )
        queue_count += 1

conn.commit()

print("? Exists:", exists_count)
print("?? Queue:", queue_count)

conn.close()
print("\nDONE.")

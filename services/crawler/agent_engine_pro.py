import sqlite3
import requests
import re
from datetime import datetime

DB = '/docker/media-stack/data/crawler/crawler_master_full.db'
AGENT_URL = 'http://10.0.0.3:5001/all_codes'

def extract_code(text):
    m = re.search(r'([A-Z0-9]+-\d+)', text.upper())
    return m.group(1) if m else None

def main():
    print("🟡 SYNC AGENT (WITH DELETE DETECTION)")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Create table if not exists
    c.execute("""
    CREATE TABLE IF NOT EXISTS agent(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        first_seen TEXT,
        last_seen TEXT,
        is_active INTEGER DEFAULT 1
    )
    """)
    conn.commit()

    # Step 1: Mark all inactive first
    c.execute("UPDATE agent SET is_active=0")
    conn.commit()

    # Step 2: Fetch live codes
    try:
        r = requests.get(AGENT_URL, timeout=20)
        raw_codes = r.json()
    except Exception as e:
        print("Agent error:", e)
        return

    now = datetime.now().isoformat()
    live_codes = set()

    for raw in raw_codes:
        code = extract_code(raw)
        if not code:
            continue

        live_codes.add(code)

        # Insert or update
        c.execute("""
        INSERT INTO agent(code, first_seen, last_seen, is_active)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(code) DO UPDATE SET
            last_seen=excluded.last_seen,
            is_active=1
        """, (code, now, now))

    conn.commit()

    print("Live codes:", len(live_codes))

    # Step 3: Detect deleted codes
    deleted = c.execute("""
        SELECT code FROM agent
        WHERE is_active=0
    """).fetchall()

    print("🔴 Deleted codes:", len(deleted))

    for d in deleted[:10]:
        print("  -", d[0])

    # Step 4: Update queue status
    try:
        c.execute("ALTER TABLE queuedqbit ADD COLUMN status TEXT")
        conn.commit()
    except:
        pass

    rows = c.execute("""
        SELECT id, code FROM queuedqbit
    """).fetchall()

    exists_count = 0
    queue_count = 0

    for row_id, code in rows:
        if code in live_codes:
            c.execute("""
                UPDATE queuedqbit
                SET status='exists'
                WHERE id=?
            """, (row_id,))
            exists_count += 1
        else:
            c.execute("""
                UPDATE queuedqbit
                SET status='queue_add'
                WHERE id=?
            """, (row_id,))
            queue_count += 1

    conn.commit()
    conn.close()

    print("✅ Exists:", exists_count)
    print("🟢 Queue Add:", queue_count)
    print("DONE.")

if __name__ == "__main__":
    main()

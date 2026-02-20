import sqlite3
import requests
import re

DB = '/docker/media-stack/data/crawler/crawler_master_full.db'
AGENT_URL = 'http://10.0.0.3:5001/all_codes'

def extract_code(text):
    m = re.search(r'([A-Z0-9]+-\d+)', text.upper())
    return m.group(1) if m else None

def main():
    print("🟡 SYNC AGENT CODES (UNIQUE MODE)")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Create agent table if not exists
    c.execute("""
    CREATE TABLE IF NOT EXISTS agent(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        first_seen TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()

    # Fetch agent folders
    try:
        r = requests.get(AGENT_URL, timeout=20)
        agent_raw = r.json()
    except Exception as e:
        print("Agent error:", e)
        return

    print("Agent folders:", len(agent_raw))

    inserted = 0
    skipped = 0

    for raw in agent_raw:
        code = extract_code(raw)
        if not code:
            continue

        try:
            c.execute("""
                INSERT INTO agent(code)
                VALUES (?)
            """, (code,))
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1

    conn.commit()

    print("Inserted:", inserted)
    print("Skipped (already exists):", skipped)

    # Load agent codes
    agent_codes = set(
        row[0].upper()
        for row in c.execute("SELECT code FROM agent").fetchall()
    )

    print("🟡 COMPARE WITH QUEUE")

    # Ensure status column exists
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
        if code.upper() in agent_codes:
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

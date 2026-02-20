import sqlite3
import requests
import re
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, 'data', 'crawler_master_full.db')
AGENT_URL = 'http://10.0.0.3:5001/all_codes'

def extract_code(text):
    m = re.search(r'([A-Z0-9]+-\d+)', text.upper())
    return m.group(1) if m else None

def main():
    print("SYNC AGENT")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    try:
        r = requests.get(AGENT_URL, timeout=20)
        raw_codes = r.json()
    except Exception as e:
        print("Agent error:", e)
        return

    live_codes = set()

    for raw in raw_codes:
        code = extract_code(raw)
        if code:
            live_codes.add(code)

    rows = c.execute("""
        SELECT id, code, status FROM queuedqbit
    """).fetchall()

    existed_count = 0

    for row_id, code, status in rows:
        if code in live_codes and status not in ('added'):
            c.execute("""
                UPDATE queuedqbit
                SET status='existed'
                WHERE id=?
            """,(row_id,))
            existed_count += 1

    conn.commit()
    conn.close()

    print("Existed:", existed_count)
    print("DONE")

if __name__ == "__main__":
    main()
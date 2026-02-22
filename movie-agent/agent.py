# -*- coding: utf-8 -*-

import os
import re
import sqlite3
import time
import sys
from datetime import datetime

BASE_PATH = "/data"
DB_PATH = "/app/data/crawler_master_full.db"
SCAN_INTERVAL = 60

VIDEO_EXT = (".mp4", ".mkv", ".avi", ".mov")


# =========================
# LOGGER
# =========================
def log(msg):
    print(f"[AGENT] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}", flush=True)


# =========================
# EXTRACT CODE
# =========================
def extract_code(text):
    m = re.search(r'\b([A-Z]{2,10}-\d{2,6})\b', text.upper())
    return m.group(1) if m else None


# =========================
# ENSURE TABLE
# =========================
def ensure_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS agent_snapshot (
            code TEXT PRIMARY KEY,
            source_type TEXT CHECK(source_type IN ('folder','file')),
            real_name TEXT,
            last_seen TEXT
        )
    """)

    try:
        c.execute("ALTER TABLE agent_snapshot ADD COLUMN real_name TEXT")
    except:
        pass

    conn.commit()
    conn.close()


# =========================
# SCAN ONCE
# =========================
def scan_once():

    if not os.path.exists(BASE_PATH):
        log(f"Movies path not found: {BASE_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    now = datetime.now().isoformat()
    found = {}

    total_items = 0
    valid_codes = 0

    for name in os.listdir(BASE_PATH):

        total_items += 1
        full_path = os.path.join(BASE_PATH, name)

        code = extract_code(name)
        if not code:
            continue

        if os.path.isdir(full_path):
            found[code] = ("folder", name)
            valid_codes += 1

        elif os.path.isfile(full_path):
            if name.lower().endswith(VIDEO_EXT):
                if code not in found:
                    found[code] = ("file", name)
                    valid_codes += 1

    # ?? update DB
    for code, value in found.items():

        source_type = value[0]
        real_name = value[1]

        c.execute("""
            INSERT INTO agent_snapshot (code, source_type, real_name, last_seen)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                source_type=?,
                real_name=?,
                last_seen=?
        """, (
            code,
            source_type,
            real_name,
            now,
            source_type,
            real_name,
            now
        ))

    conn.commit()
    conn.close()

    log(f"Scan complete | Total items: {total_items} | Valid codes: {valid_codes}")


# =========================
# RUN ONCE
# =========================
def run_once():
    ensure_table()
    scan_once()


# =========================
# LOOP MODE
# =========================
def main():
    log("Movie Agent started")
    ensure_table()

    while True:
        try:
            scan_once()
        except Exception as e:
            log(f"ERROR: {e}")

        time.sleep(SCAN_INTERVAL)


# =========================
# ENTRY
# =========================
if __name__ == "__main__":

    if len(sys.argv) > 1 and sys.argv[1] == "once":
        run_once()
    else:
        main()
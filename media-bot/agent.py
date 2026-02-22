# -*- coding: utf-8 -*-

import os
import re
import sqlite3
import time
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
# UTILS
# =========================
def extract_code(text):
    m = re.search(r'([A-Z0-9]+-\d+)', text.upper())
    return m.group(1) if m else None


# =========================
# DB TABLE
# =========================
def ensure_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS agent_snapshot (
            code TEXT PRIMARY KEY,
            source_type TEXT CHECK(source_type IN ('folder','file')),
            last_seen TEXT
        )
    """)
    conn.commit()
    conn.close()
    log("agent_snapshot table ensured")


# =========================
# SCAN CORE
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
            found[code] = "folder"
            valid_codes += 1

        elif os.path.isfile(full_path):
            if name.lower().endswith(VIDEO_EXT):
                if code not in found:
                    found[code] = "file"
                    valid_codes += 1

    for code, source_type in found.items():
        c.execute("""
            INSERT INTO agent_snapshot (code, source_type, last_seen)
            VALUES (?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                source_type=excluded.source_type,
                last_seen=excluded.last_seen
        """, (code, source_type, now))

    conn.commit()
    conn.close()

    log(f"Scan complete | Total items: {total_items} | Valid codes: {valid_codes}")


# =========================
# RUN ONCE (CHO RUNNER)
# =========================
def run_once():
    ensure_table()
    scan_once()


# =========================
# LOOP MODE
# =========================
def main():
    log("Movie Agent started")
    log(f"Scanning path: {BASE_PATH}")
    ensure_table()

    while True:
        try:
            scan_once()
        except Exception as e:
            log(f"ERROR: {e}")

        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    main()
import sqlite3
import os
from logger_core import log

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "data", "crawler_master_full.db")

def build_queue():
    log("TOOL2", "START", "Building queue")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS queuedqbit(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        torrent_url TEXT,
        status TEXT DEFAULT 'new'
    )
    """)

    rows = c.execute("SELECT code, torrent_url FROM crawl").fetchall()

    inserted = 0

    for code, url in rows:
        try:
            c.execute("""
                INSERT OR IGNORE INTO queuedqbit(code, torrent_url)
                VALUES (?,?)
            """, (code, url))
            if c.rowcount > 0:
                inserted += 1
        except:
            pass

    conn.commit()
    conn.close()

    log("TOOL2", "FINISH", f"Inserted {inserted} new items")
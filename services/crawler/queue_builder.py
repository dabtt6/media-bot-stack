import sqlite3
from datetime import datetime

DB = '/docker/media-stack/data/crawler/crawler_master_test.db'

conn = sqlite3.connect(DB)
c = conn.cursor()

# =========================
# CREATE TABLE IF NOT EXISTS
# =========================
c.execute('''
CREATE TABLE IF NOT EXISTS queuedqbit(
id INTEGER PRIMARY KEY AUTOINCREMENT,
actor_name TEXT,
code TEXT UNIQUE,
chosen_source TEXT,
torrent_url TEXT,
size_mb REAL,
seeds INTEGER,
date_ts REAL,
status TEXT,
created_at TEXT
)
''')
conn.commit()

print("\n🟡 BUILD QUEUE")

# =========================
# GET ALL UNIQUE CODES
# =========================
codes = c.execute("SELECT DISTINCT code FROM crawl").fetchall()

print("Total codes:", len(codes))

for (code,) in codes:
    rows = c.execute("""
        SELECT actor_name, source, torrent_url, size_mb, seeds, date_ts
        FROM crawl
        WHERE code=?
    """, (code,)).fetchall()

    if not rows:
        continue

    # Separate ijav and onejav
    ijav = [r for r in rows if r[1] == "ijav"]
    onejav = [r for r in rows if r[1] == "onejav"]

    chosen = None

    # Priority IJAV
    if ijav:
        ijav.sort(key=lambda x: (x[5], x[3], x[4]), reverse=True)
        chosen = ijav[0]
    else:
        onejav.sort(key=lambda x: (x[5], x[3], x[4]), reverse=True)
        chosen = onejav[0]

    actor_name, source, url, size, seeds, date_ts = chosen

    c.execute("""
        INSERT OR IGNORE INTO queuedqbit
        (actor_name, code, chosen_source, torrent_url, size_mb, seeds, date_ts, status, created_at)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        actor_name,
        code,
        source,
        url,
        size,
        seeds,
        date_ts,
        "queue",
        datetime.now().isoformat()
    ))

conn.commit()

print("Queue built successfully.")
print("Queued items:", c.execute("SELECT COUNT(*) FROM queuedqbit").fetchone()[0])

conn.close()

print("\nDONE.")

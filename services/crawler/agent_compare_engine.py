import sqlite3

DB = '/docker/media-stack/data/crawler/crawler_master_test.db'

conn = sqlite3.connect(DB)
c = conn.cursor()

# =========================
# INIT AGENT TABLE
# =========================
c.execute('''
CREATE TABLE IF NOT EXISTS agent(
id INTEGER PRIMARY KEY AUTOINCREMENT,
code TEXT UNIQUE,
source TEXT,
size_mb REAL,
added_at TEXT
)
''')

conn.commit()

print("\n🟡 BUILD AGENT TABLE OK")

# =========================
# LOAD AGENT CODES
# (giả lập: nếu sau này sync từ qbit thì insert vào đây)
# =========================

agent_codes = set(
    row[0] for row in c.execute("SELECT code FROM agent").fetchall()
)

print("Agent codes:", len(agent_codes))

# =========================
# COMPARE WITH QUEUE
# =========================

rows = c.execute("""
SELECT id, code FROM queuedqbit
WHERE status IS NULL OR status='queue'
""").fetchall()

ready_count = 0

for row_id, code in rows:
    if code not in agent_codes:
        c.execute("""
        UPDATE queuedqbit
        SET status='ready_add'
        WHERE id=?
        """, (row_id,))
        ready_count += 1
    else:
        c.execute("""
        UPDATE queuedqbit
        SET status='skip_agent'
        WHERE id=?
        """, (row_id,))

conn.commit()

print("Ready to add:", ready_count)

# =========================
# SUMMARY
# =========================

total_ready = c.execute("""
SELECT COUNT(*) FROM queuedqbit
WHERE status='ready_add'
""").fetchone()[0]

total_skip = c.execute("""
SELECT COUNT(*) FROM queuedqbit
WHERE status='skip_agent'
""").fetchone()[0]

print("READY_ADD:", total_ready)
print("SKIP_AGENT:", total_skip)

print("\nDONE.")

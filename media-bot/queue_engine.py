import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, 'data', 'crawler_master_full.db')

def build_queue():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    print("BUILD QUEUE (STATE = NEW)")

    codes = c.execute("SELECT DISTINCT code FROM crawl").fetchall()

    for row in codes:
        code = row[0]

        rows = c.execute("""
            SELECT actor_name, source, torrent_url, size_mb, seeds, date_ts
            FROM crawl
            WHERE code=?
        """,(code,)).fetchall()

        if not rows:
            continue

        max_seed = max(r[4] for r in rows)

        if max_seed >= 50:
            rows.sort(key=lambda x: x[3], reverse=True)
        else:
            rows.sort(key=lambda x: (x[3], x[5], x[4]), reverse=True)

        best = rows[0]

        c.execute("""
            INSERT INTO queuedqbit
            (code, actor_name, chosen_source, torrent_url, size_mb, seeds, date_ts, status, retry_count)
            VALUES (?,?,?,?,?,?,?, 'new', 0)
            ON CONFLICT(code) DO NOTHING
        """,(code, best[0], best[1], best[2], best[3], best[4], best[5]))

        print("?", best[0], "|", code)

    conn.commit()
    conn.close()
    print("QUEUE BUILD DONE")

if __name__ == "__main__":
    build_queue()
# -*- coding: utf-8 -*-

import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "data", "crawler_master_full.db")


def get_conn():
    return sqlite3.connect(DB)


def build_queue():

    print("\nTOOL 2 - BUILD QUEUE")

    conn = get_conn()
    c = conn.cursor()

    # =============================
    # L?y code dã có trên disk
    # =============================
    agent_codes = set(
        row[0] for row in c.execute("SELECT code FROM agent_snapshot")
    )

    # =============================
    # L?y t?t c? code t? crawl
    # =============================
    codes = c.execute("""
        SELECT DISTINCT code
        FROM crawl
        WHERE code IS NOT NULL
    """).fetchall()

    new_count = 0
    existed_count = 0
    updated_count = 0
    skipped_count = 0

    for (code,) in codes:

        # =============================
        # L?y t?t c? torrent c?a code dó
        # =============================
        rows = c.execute("""
            SELECT actor_name, torrent_url,
                   size_mb, seeds, date_ts
            FROM crawl
            WHERE code=?
        """, (code,)).fetchall()

        if not rows:
            continue

        # =============================
        # Ranking:
        # Seeds > Date > Size
        # =============================
        best = max(rows, key=lambda r: (
            r[3] or 0,   # seeds
            r[4] or 0,   # date_ts
            r[2] or 0    # size
        ))

        actor, url, size_mb, seeds, date_ts = best

        # =============================
        # Ki?m tra dã t?n t?i trong queue chua
        # =============================
        existing = c.execute("""
            SELECT status
            FROM queuedqbit
            WHERE code=?
        """, (code,)).fetchone()

        if existing:

            old_status = existing[0]

            # N?u dã added ho?c existed ? b? qua
            if old_status in ("added", "existed"):
                skipped_count += 1
                continue

            # N?u error ? update torrent m?i + reset retry
            if old_status == "error":
                c.execute("""
                    UPDATE queuedqbit
                    SET actor_name=?,
                        torrent_url=?,
                        size_mb=?,
                        seeds=?,
                        status='new',
                        retry_count=0,
                        last_try_at=NULL
                    WHERE code=?
                """, (
                    actor,
                    url,
                    size_mb,
                    seeds,
                    code
                ))
                updated_count += 1
                continue

            # N?u new ? b? qua
            skipped_count += 1
            continue

        # =============================
        # N?u chua t?n t?i trong queue
        # =============================
        if code in agent_codes:
            status = "existed"
            existed_count += 1
        else:
            status = "new"
            new_count += 1

        c.execute("""
            INSERT INTO queuedqbit
            (code, actor_name, torrent_url,
             size_mb, seeds, status, created_at)
            VALUES (?,?,?,?,?,?,?)
        """, (
            code,
            actor,
            url,
            size_mb,
            seeds,
            status,
            datetime.now().isoformat()
        ))

    conn.commit()
    conn.close()

    print("New:", new_count)
    print("Existed:", existed_count)
    print("Updated (retry):", updated_count)
    print("Skipped:", skipped_count)
    print("DONE\n")


if __name__ == "__main__":
    build_queue()
# -*- coding: utf-8 -*-

import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "data", "crawler_master_full.db")

def build_queue():

    print("?? TOOL 2 - BUILD QUEUE")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # L?y danh sách code dã t?n t?i trong movies (agent snapshot)
    agent_codes = set(
        row[0] for row in c.execute("SELECT code FROM agent_snapshot")
    )

    # L?y danh sách code dã có trong queue
    existing_queue = set(
        row[0] for row in c.execute("SELECT code FROM queuedqbit")
    )

    # L?y danh sách code t? crawl
    codes = c.execute("SELECT DISTINCT code FROM crawl").fetchall()

    new_count = 0
    existed_count = 0
    skipped_count = 0

    for (code,) in codes:

        # N?u dã có trong queue thì b? qua
        if code in existing_queue:
            skipped_count += 1
            continue

        # L?y t?t c? source c?a code dó
        rows = c.execute("""
            SELECT actor_name, torrent_url, size_mb, seeds
            FROM crawl
            WHERE code=?
        """, (code,)).fetchall()

        if not rows:
            continue

        # Ch?n torrent t?t nh?t (uu tiên seeds, sau dó size)
        best = max(rows, key=lambda x: (x[3], x[2]))
        actor, url, size_mb, seeds = best

        # N?u dã t?n t?i trên disk
        if code in agent_codes:
            status = "existed"
            existed_count += 1
        else:
            status = "new"
            new_count += 1

        c.execute("""
            INSERT INTO queuedqbit
            (code, actor_name, torrent_url, size_mb, seeds, status, created_at)
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
    print("Skipped (already in queue):", skipped_count)
    print("DONE")

if __name__ == "__main__":
    build_queue()
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

    agent_codes = set(
        row[0] for row in c.execute("SELECT code FROM agent").fetchall()
    )

    existing_queue = set(
        row[0] for row in c.execute("SELECT code FROM queuedqbit").fetchall()
    )

    crawl_rows = c.execute("""
        SELECT code, actor_name, torrent_url, size_mb, seeds
        FROM crawl
    """).fetchall()

    new_count = 0
    existed_count = 0

    for code, actor, url, size_mb, seeds in crawl_rows:

        if code in existing_queue:
            continue

        status = "existed" if code in agent_codes else "new"

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

        if status == "new":
            new_count += 1
        else:
            existed_count += 1

    conn.commit()
    conn.close()

    print("New:", new_count)
    print("Existed:", existed_count)
    print("DONE")

if __name__ == "__main__":
    build_queue()
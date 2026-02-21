# -*- coding: utf-8 -*-

import sqlite3
import requests
import os
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "data", "crawler_master_full.db")

QBIT_URL = os.getenv("QBIT_URL")
QBIT_USER = os.getenv("QBIT_USER")
QBIT_PASS = os.getenv("QBIT_PASS")

MAX_RETRY = 3
SLEEP_TIME = 5

SESSION = requests.Session()

# =========================
# LOGGING
# =========================
os.makedirs("logs", exist_ok=True)

logger = logging.getLogger("QUEUE_WORKER")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s",
    "%Y-%m-%d %H:%M:%S"
)

file_handler = RotatingFileHandler(
    "logs/worker.log",
    maxBytes=10 * 1024 * 1024,
    backupCount=5
)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# =========================
# DB CONNECT
# =========================
def get_conn():
    conn = sqlite3.connect(DB, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


# =========================
# LOGIN QBIT
# =========================
def login():
    while True:
        try:
            r = SESSION.post(
                QBIT_URL + "/api/v2/auth/login",
                data={"username": QBIT_USER, "password": QBIT_PASS},
                timeout=10
            )
            if r.text == "Ok.":
                logger.info("qBit connected")
                return
        except:
            pass

        logger.warning("Waiting for qBit...")
        time.sleep(5)


# =========================
# RESET STUCK
# =========================
def reset_stuck():
    conn = get_conn()
    conn.execute("""
        UPDATE queuedqbit
        SET status='error'
        WHERE status='adding'
    """)
    conn.commit()
    conn.close()


# =========================
# SYNC WITH AGENT (SELF-HEALING)
# =========================
def sync_with_agent():
    conn = get_conn()
    c = conn.cursor()

    agent_codes = set(
        r[0] for r in c.execute("SELECT code FROM agent_snapshot")
    )

    rows = c.execute("""
        SELECT id, code, status
        FROM queuedqbit
        WHERE status IN ('new','adding','added','error')
    """).fetchall()

    for row_id, code, status in rows:
        if code in agent_codes:
            c.execute("""
                UPDATE queuedqbit
                SET status='existed'
                WHERE id=?
            """, (row_id,))
            logger.info(f"Synced to existed: {code}")

    conn.commit()
    conn.close()


# =========================
# BUILD QUEUE (Tool2 logic)
# =========================
def build_queue():
    conn = get_conn()
    c = conn.cursor()

    agent_codes = set(
        r[0] for r in c.execute("SELECT code FROM agent_snapshot")
    )

    codes = c.execute("""
        SELECT DISTINCT code
        FROM crawl
        WHERE code IS NOT NULL
    """).fetchall()

    for (code,) in codes:

        existing = c.execute(
            "SELECT status FROM queuedqbit WHERE code=?",
            (code,)
        ).fetchone()

        if existing:
            if code in agent_codes and existing[0] != "existed":
                c.execute("""
                    UPDATE queuedqbit
                    SET status='existed'
                    WHERE code=?
                """, (code,))
                logger.info(f"Updated to existed: {code}")
            continue

        rows = c.execute("""
            SELECT actor_name, torrent_url,
                   size_mb, seeds, date_ts
            FROM crawl
            WHERE code=?
        """, (code,)).fetchall()

        if not rows:
            continue

        best = max(rows, key=lambda r: (
            r[3] or 0,
            r[4] or 0,
            r[2] or 0
        ))

        actor, url, size_mb, seeds, _ = best
        status = "existed" if code in agent_codes else "new"

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

        logger.info(f"Queued {code} ({status})")

    conn.commit()
    conn.close()


# =========================
# ADD TORRENT (Tool4 logic)
# =========================
def add_torrent():
    conn = get_conn()
    c = conn.cursor()

    row = c.execute("""
        SELECT id, code, torrent_url
        FROM queuedqbit
        WHERE status='new'
           OR (status='error' AND retry_count < ?)
        LIMIT 1
    """, (MAX_RETRY,)).fetchone()

    if not row:
        conn.close()
        return

    row_id, code, url = row

    try:
        c.execute("UPDATE queuedqbit SET status='adding' WHERE id=?", (row_id,))
        conn.commit()

        r = requests.get(url, timeout=30)
        files = {"torrents": ("file.torrent", r.content)}

        SESSION.post(
            QBIT_URL + "/api/v2/torrents/add",
            files=files,
            timeout=30
        )

        c.execute("""
            UPDATE queuedqbit
            SET status='added',
                added_at=?,
                retry_count=0
            WHERE id=?
        """, (datetime.now().isoformat(), row_id))

        conn.commit()
        logger.info(f"Added {code}")

    except Exception as e:
        c.execute("""
            UPDATE queuedqbit
            SET status='error',
                retry_count=retry_count+1,
                last_try_at=?
            WHERE id=?
        """, (datetime.now().isoformat(), row_id))

        conn.commit()
        logger.error(f"Add failed {code} | {str(e)}")

    conn.close()


# =========================
# MONITOR COMPLETE (Tool5 logic)
# =========================
def monitor_complete():
    try:
        torrents = SESSION.get(
            QBIT_URL + "/api/v2/torrents/info",
            timeout=20
        ).json()
    except:
        return

    completed = {t["name"] for t in torrents if t["progress"] == 1.0}

    if not completed:
        return

    conn = get_conn()
    c = conn.cursor()

    rows = c.execute("""
        SELECT id, code
        FROM queuedqbit
        WHERE status='added'
    """).fetchall()

    for row_id, code in rows:
        if code in completed:
            c.execute("""
                UPDATE queuedqbit
                SET status='completed',
                    completed_at=?
                WHERE id=?
            """, (datetime.now().isoformat(), row_id))

            logger.info(f"Completed {code}")

    conn.commit()
    conn.close()


# =========================
# MAIN LOOP
# =========================
def main():
    logger.info("Queue Worker Started")

    login()
    reset_stuck()

    while True:
        try:
            sync_with_agent()
            build_queue()
            add_torrent()
            monitor_complete()
        except Exception as e:
            logger.critical(f"Worker crash: {str(e)}")
            login()

        time.sleep(SLEEP_TIME)


if __name__ == "__main__":
    main()
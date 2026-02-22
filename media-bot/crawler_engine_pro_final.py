# -*- coding: utf-8 -*-

import sqlite3
import requests
import re
import time
import threading
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "data", "crawler_master_full.db")
HEADERS = {"User-Agent": "Mozilla/5.0"}

MAX_RETRY = 3
MAX_PAGE = 10
SLEEP_BETWEEN_MOVIE = 0.15


# =========================
# LOGGER
# =========================
def log(msg):
    print(f"{datetime.now().strftime('%H:%M:%S')} | {msg}", flush=True)


# =========================
# DB CONNECT
# =========================
def get_conn():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


# =========================
# ERROR TABLE
# =========================
def record_error(actor_name, source, error_msg):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()

    row = c.execute("""
        SELECT retry_count FROM crawl_error
        WHERE actor_name=? AND source=?
    """, (actor_name, source)).fetchone()

    if row:
        retry = row[0] + 1
        c.execute("""
            UPDATE crawl_error
            SET retry_count=?, last_try_at=?, error_message=?
            WHERE actor_name=? AND source=?
        """, (retry, now, error_msg, actor_name, source))
    else:
        c.execute("""
            INSERT INTO crawl_error
            (actor_name, source, error_message,
             retry_count, last_try_at, created_at)
            VALUES (?,?,?,?,?,?)
        """, (actor_name, source, error_msg, 1, now, now))

    conn.commit()
    conn.close()


def clear_error(actor_name, source):
    conn = get_conn()
    conn.execute("""
        DELETE FROM crawl_error
        WHERE actor_name=? AND source=?
    """, (actor_name, source))
    conn.commit()
    conn.close()


# =========================
# UTILS
# =========================
def parse_size(text):
    text = text.lower().replace(" ", "")
    if "gb" in text:
        return float(text.replace("gb", "")) * 1024
    if "mb" in text:
        return float(text.replace("mb", ""))
    return 0


def parse_date(text):
    try:
        return datetime.strptime(text.strip(), "%d/%m/%Y").timestamp()
    except:
        return 0


def extract_code(text):
    m = re.search(r'([A-Z0-9]+-\d+)', text.upper())
    return m.group(1) if m else None


def extract_code_from_onejav(url):
    m = re.search(r'/torrent/([a-z0-9]+)/', url.lower())
    if not m:
        return None

    raw = m.group(1)
    m2 = re.match(r'([a-z]+)(\d+)', raw)
    if not m2:
        return raw.upper()

    return f"{m2.group(1).upper()}-{m2.group(2)}"


# =========================
# IJAV MULTI PAGE
# =========================
def crawl_ijav(actor_name, actor_url):

    log(f"IJAV START: {actor_name}")

    conn = get_conn()
    c = conn.cursor()

    total_insert = 0

    try:

        for page in range(1, MAX_PAGE + 1):

            url = actor_url if page == 1 else actor_url + f"?page={page}"

            log(f"{actor_name} | Page {page}")

            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")

            movie_links = [
                urljoin(url, a["href"])
                for a in soup.select("div.name a")
            ]

            if not movie_links:
                break

            new_insert_this_page = 0

            for m in movie_links:

                try:
                    time.sleep(SLEEP_BETWEEN_MOVIE)

                    code = extract_code(m)
                    if not code:
                        continue

                    exists = c.execute(
                        "SELECT 1 FROM crawl WHERE code=?",
                        (code,)
                    ).fetchone()

                    if exists:
                        continue

                    rm = requests.get(m, headers=HEADERS, timeout=15)
                    msoup = BeautifulSoup(rm.text, "html.parser")

                    torrents = []

                    for tr in msoup.find_all("tr"):
                        text = tr.get_text(" ", strip=True)

                        if "#" in text and "Download" in text:

                            size_match = re.search(r'(\d+(\.\d+)?)(gb|mb)', text.lower())
                            size = parse_size(size_match.group()) if size_match else 0

                            seeds_match = re.search(r'Seeds\s*(\d+)', text)
                            seeds = int(seeds_match.group(1)) if seeds_match else 0

                            date_match = re.search(r'\d{2}/\d{2}/\d{4}', text)
                            date_ts = parse_date(date_match.group()) if date_match else 0

                            dl = None
                            for a in tr.find_all("a", href=True):
                                if "/download/" in a["href"]:
                                    dl = urljoin(url, a["href"])
                                    break

                            if size > 0 and dl:
                                torrents.append((size, seeds, date_ts, dl))

                    if torrents:
                        torrents.sort(key=lambda x: (x[1], x[2], x[0]), reverse=True)
                        best = torrents[0]

                        now = datetime.now().isoformat()

                        c.execute("""
                            INSERT INTO crawl
                            (actor_name, source, code, torrent_url,
                             size_mb, seeds, date_ts, created_at, last_seen)
                            VALUES (?,?,?,?,?,?,?,?,?)
                        """, (
                            actor_name, "ijav", code,
                            best[3], best[0], best[1], best[2],
                            now, now
                        ))

                        conn.commit()

                        total_insert += 1
                        new_insert_this_page += 1

                        log(f"{actor_name} | NEW {code}")

                except:
                    continue

            if page == 1 and new_insert_this_page == 0:
                log(f"{actor_name} | No new on page 1 → STOP")
                break

        clear_error(actor_name, "ijav")
        log(f"IJAV DONE: {actor_name} | Total New: {total_insert}")

    except Exception as e:
        record_error(actor_name, "ijav", str(e))
        log(f"IJAV ERROR: {actor_name} | {str(e)}")

    finally:
        conn.close()


# =========================
# ONEJAV
# =========================
def crawl_onejav(actor_name, actor_url):

    log(f"ONEJAV START: {actor_name}")

    conn = get_conn()
    c = conn.cursor()
    total_insert = 0

    try:

        r = requests.get(actor_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.find_all("a", href=True):

            if "/torrent/" in a["href"] and "/download/" in a["href"]:

                link = urljoin(actor_url, a["href"])
                code = extract_code_from_onejav(link)

                if not code:
                    continue

                exists = c.execute(
                    "SELECT 1 FROM crawl WHERE code=?",
                    (code,)
                ).fetchone()

                if exists:
                    continue

                now = datetime.now().isoformat()

                c.execute("""
                    INSERT INTO crawl
                    (actor_name, source, code, torrent_url,
                     size_mb, seeds, date_ts, created_at, last_seen)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    actor_name, "onejav", code,
                    link, 0, 0, 0,
                    now, now
                ))

                conn.commit()
                total_insert += 1
                log(f"{actor_name} | NEW {code}")

        clear_error(actor_name, "onejav")
        log(f"ONEJAV DONE: {actor_name} | Total New: {total_insert}")

    except Exception as e:
        record_error(actor_name, "onejav", str(e))
        log(f"ONEJAV ERROR: {actor_name} | {str(e)}")

    finally:
        conn.close()


# =========================
# MAIN
# =========================
def main():

    log("TOOL 1 STARTED")

    conn = get_conn()
    actors = conn.execute("SELECT name, source, url FROM actors").fetchall()
    conn.close()

    threads = []

    for name, source, url in actors:

        if source == "ijav":
            target = crawl_ijav
        elif source == "onejav":
            target = crawl_onejav
        else:
            continue

        t = threading.Thread(target=target, args=(name, url))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    log("TOOL 1 DONE")


if __name__ == "__main__":
    main()
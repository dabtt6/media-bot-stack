import sqlite3
import requests
import datetime
import re
import os
import time
import threading
import random
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import bencodepy

DB_NAME = "/app/data/crawler.db"
HEADERS = {"User-Agent": "Mozilla/5.0"}
QBIT_URL = os.getenv("QBIT_URL")
QBIT_USER = os.getenv("QBIT_USER")
QBIT_PASS = os.getenv("QBIT_PASS")
AGENT_URL = os.getenv("AGENT_URL")

MAX_WORKERS = 3
MAX_RETRY = 3

db_queue = Queue()

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ================= DB WRITER =================
def db_writer():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA busy_timeout=5000;")
    conn.commit()

    while True:
        sql, params = db_queue.get()
        try:
            c.execute(sql, params)
            conn.commit()
        except Exception as e:
            log(f"[DB ERROR] {e}")
        db_queue.task_done()

# ================= UTIL =================
def extract_code(text):
    m = re.search(r'([A-Z]{2,10}-\d{2,6})', text.upper())
    return m.group(1) if m else None

def qbit_login():
    s = requests.Session()
    try:
        r = s.post(f"{QBIT_URL}/api/v2/auth/login",
                   data={"username":QBIT_USER,"password":QBIT_PASS})
        if r.text == "Ok.":
            return s
    except:
        pass
    return None

def agent_has_code(code):
    try:
        r = requests.get(f"{AGENT_URL}/has_code/{code}", timeout=5)
        return r.json().get("exists", False)
    except:
        return False

# ================= CRAWL =================
def crawl_engine():
    while True:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT name,url FROM actors")
        actors = c.fetchall()
        conn.close()

        for name,page_url in actors:
            try:
                r = requests.get(page_url, headers=HEADERS, timeout=15)
                soup = BeautifulSoup(r.text,"html.parser")

                for a in soup.find_all("a",href=True):
                    if "/download/" in a["href"]:
                        full_url = urljoin(page_url,a["href"])
                        db_queue.put((
                            "INSERT OR IGNORE INTO downloads (actor_name,torrent_url,status,retry_count,created_at) VALUES (?,?, 'new',0, ?)",
                            (name,full_url,datetime.datetime.now().isoformat())
                        ))
            except:
                pass

        time.sleep(120)

# ================= DOWNLOAD =================
def download_task(row):
    fid, url, retry = row

    try:
        log(f"[DOWNLOAD] {fid}")
        time.sleep(random.uniform(1.0,2.0))

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://onejav.com/"
        }

        r = requests.get(url,
                         headers=headers,
                         timeout=60,
                         allow_redirects=True)

        if r.status_code != 200:
            raise Exception(f"HTTP {r.status_code}")

        meta = bencodepy.decode(r.content)
        name = meta[b'info'][b'name'].decode(errors="ignore")
        size = meta[b'info'].get(b'length', 0)
        code = extract_code(name)

        # Agent check
        if code and agent_has_code(code):
            log(f"[SKIP AGENT] {code}")
            db_queue.put(("UPDATE downloads SET status='exists' WHERE id=?", (fid,)))
            return

        q = qbit_login()
        if not q:
            raise Exception("qBit login fail")

        torrents = q.get(f"{QBIT_URL}/api/v2/torrents/info").json()

        same_code = [t for t in torrents if code and code in t["name"].upper()]

        if same_code:
            largest = max(same_code, key=lambda x: x.get("total_size",0))
            if size > largest.get("total_size",0):
                log(f"[REPLACE] {code} bigger version")
                q.post(f"{QBIT_URL}/api/v2/torrents/delete",
                       data={"hashes":largest["hash"],"deleteFiles":"true"})
            else:
                log(f"[SKIP QB] {code} smaller")
                db_queue.put(("UPDATE downloads SET status='added' WHERE id=?", (fid,)))
                return

        fn = f"{fid}.torrent"
        with open(fn,"wb") as f:
            f.write(r.content)

        q.post(f"{QBIT_URL}/api/v2/torrents/add",
               files={"torrents":open(fn,"rb")})

        os.remove(fn)

        db_queue.put(("UPDATE downloads SET status='added' WHERE id=?", (fid,)))
        log(f"[ADDED] {name}")

    except Exception as e:
        if retry < MAX_RETRY:
            backoff = 5 * (retry + 1)
            log(f"[RETRY] {fid} -> {str(e)} (sleep {backoff}s)")
            time.sleep(backoff)
            db_queue.put(("UPDATE downloads SET retry_count=retry_count+1 WHERE id=?", (fid,)))
        else:
            log(f"[FAIL] {fid} -> {str(e)}")
            db_queue.put(("UPDATE downloads SET status='error' WHERE id=?", (fid,)))

def download_engine():
    while True:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id,torrent_url,retry_count FROM downloads WHERE status='new'")
        rows = c.fetchall()
        conn.close()

        if rows:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
                futures = [exe.submit(download_task, r) for r in rows]

        time.sleep(20)

# ================= SYNC =================
def sync_engine():
    while True:
        q = qbit_login()
        if not q:
            time.sleep(30)
            continue

        torrents = q.get(f"{QBIT_URL}/api/v2/torrents/info").json()

        for t in torrents:
            code = extract_code(t["name"])
            state = t["state"]

            if state == "seeding":
                status = "completed"
            elif state in ["downloading","stalledDL"]:
                status = "downloading"
            else:
                status = "added"

            db_queue.put((
                "UPDATE downloads SET status=? WHERE torrent_url LIKE ?",
                (status,f"%{code}%")
            ))

        time.sleep(60)

# ================= MAIN =================
if __name__ == "__main__":
    log("Crawler PRO FULL started")

    threading.Thread(target=db_writer,daemon=True).start()
    threading.Thread(target=crawl_engine,daemon=True).start()
    threading.Thread(target=download_engine,daemon=True).start()
    threading.Thread(target=sync_engine,daemon=True).start()

    while True:
        time.sleep(9999)

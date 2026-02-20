import random
import time
import requests
import bencodepy
from app import extract_code, qbit_login, agent_has_code, db_queue, log, QBIT_URL

MAX_RETRY = 3
HEADERS = {"User-Agent": "Mozilla/5.0"}

def download_task(row):
    fid, url, retry = row
    try:
        log(f"[DOWNLOAD] {fid}")
        time.sleep(random.uniform(1.0, 2.5))

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

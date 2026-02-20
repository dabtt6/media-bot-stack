import sqlite3
import requests
import re
import time
import threading
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

DB = "/docker/media-stack/data/crawler/crawler_master_full.db"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# DB SAFE CONNECT
# =========================
def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

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
# IJAV CRAWL
# =========================
def crawl_ijav(actor_name, actor_url):
    print(f"\n?? IJAV: {actor_name}")

    conn = get_conn()
    c = conn.cursor()

    r = requests.get(actor_url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    movie_links = [
        urljoin(actor_url, a["href"])
        for a in soup.select("div.name a")
    ]

    print("Movies:", len(movie_links))

    for m in movie_links:
        try:
            time.sleep(0.6)
            rm = requests.get(m, headers=HEADERS, timeout=20)
            msoup = BeautifulSoup(rm.text, "html.parser")

            code = extract_code(m)
            if not code:
                continue

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
                            dl = urljoin(actor_url, a["href"])
                            break

                    if size > 0 and dl:
                        torrents.append((size, seeds, date_ts, dl))

            if torrents:
                torrents.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
                best = torrents[0]

                c.execute("""
                    INSERT OR IGNORE INTO crawl
                    (actor_name,source,code,torrent_url,size_mb,seeds,date_ts)
                    VALUES(?,?,?,?,?,?,?)
                """, (actor_name, "ijav", code,
                      best[3], best[0], best[1], best[2]))

                conn.commit()

                print(f"? {code} | {round(best[0],1)}MB | Seeds:{best[1]}")

        except Exception as e:
            print("Error:", e)

    conn.close()

# =========================
# ONEJAV CRAWL
# =========================
def crawl_onejav(actor_name, actor_url):
    print(f"\n?? ONEJAV: {actor_name}")

    conn = get_conn()
    c = conn.cursor()

    r = requests.get(actor_url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    links = []
    for a in soup.find_all("a", href=True):
        if "/torrent/" in a["href"] and "/download/" in a["href"]:
            links.append(urljoin(actor_url, a["href"]))

    print("Torrent links:", len(links))

    for link in links:
        try:
            code = extract_code_from_onejav(link)
            if not code:
                continue

            c.execute("""
                INSERT OR IGNORE INTO crawl
                (actor_name,source,code,torrent_url,size_mb,seeds,date_ts)
                VALUES(?,?,?,?,?,?,?)
            """, (actor_name, "onejav", code,
                  link, 0, 0, 0))

            conn.commit()

        except Exception as e:
            print("Error:", e)

    conn.close()

# =========================
# MAIN
# =========================
def main():
    conn = get_conn()
    actors = conn.execute("SELECT name, source, url FROM actors").fetchall()
    conn.close()

    threads = []

    for name, source, url in actors:
        if source == "ijav":
            t = threading.Thread(target=crawl_ijav, args=(name, url))
        else:
            t = threading.Thread(target=crawl_onejav, args=(name, url))

        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print("\n?? TOOL 1 DONE")

if __name__ == "__main__":
    main()

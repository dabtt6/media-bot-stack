import requests
import sqlite3
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import time

HEADERS = {"User-Agent": "Mozilla/5.0"}
DB_PATH = "/app/data/crawler.db"

def parse_size(text):
    text = text.lower().replace(" ", "")
    if "gb" in text:
        return float(text.replace("gb","")) * 1024
    if "mb" in text:
        return float(text.replace("mb",""))
    return 0

def extract_code(text):
    match = re.search(r'([A-Z]{2,10}-\d{2,6})', text.upper())
    return match.group(1) if match else None

def get_actors():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name,url FROM actors")
    rows = c.fetchall()
    conn.close()
    return rows

def get_db_size(code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT size FROM downloads WHERE code=? ORDER BY size DESC LIMIT 1",(code,))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0]
    return None

def crawl_movie(movie_url):
    r = requests.get(movie_url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    torrents = []

    for a in soup.find_all("a", href=True):
        if "/download/" not in a["href"]:
            continue

        parent = a
        found_size = 0

        for _ in range(5):
            parent = parent.parent
            if not parent:
                break

            text = parent.get_text(" ", strip=True)
            match = re.search(r'([\d\.]+\s?(GB|MB))', text, re.I)
            if match:
                found_size = parse_size(match.group(1))
                break

        if found_size > 0:
            torrents.append({
                "size": found_size,
                "download": urljoin(movie_url, a["href"])
            })

    if not torrents:
        return None

    return max(torrents, key=lambda x: x["size"])

def test_actor(name, actress_url):
    print("\n====================================================")
    print("ACTOR:", name)

    r = requests.get(actress_url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    movie_links = []

    for a in soup.find_all("a", href=True):
        if "/movie/" in a["href"]:
            full = urljoin(actress_url, a["href"])
            if full not in movie_links:
                movie_links.append(full)

    print("Movies found:", len(movie_links))

    for movie in movie_links:
        try:
            code = extract_code(movie)
            if not code:
                continue

            largest = crawl_movie(movie)
            if not largest:
                continue

            db_size = get_db_size(code)

            if db_size is None:
                status = "NEW"
            elif largest["size"] > db_size:
                status = "LARGER (upgrade)"
            elif largest["size"] < db_size:
                status = "SMALLER (skip)"
            else:
                status = "EXISTS"

            print("--------------------------------------------------")
            print("CODE:", code)
            print("HTML SIZE:", round(largest["size"],2))
            print("DB SIZE:", db_size)
            print("STATUS:", status)

            time.sleep(0.2)

        except Exception as e:
            print("ERROR:", e)

def main():
    actors = get_actors()
    print("TOTAL ACTORS:", len(actors))

    for name, url in actors:
        if "ijavtorrent" not in url:
            continue
        test_actor(name, url)

if __name__ == "__main__":
    main()

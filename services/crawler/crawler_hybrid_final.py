import requests
import sqlite3
import re
import bencodepy
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9"
}

DB_PATH = "/app/data/crawler_test.db"

# =========================
# UTIL
# =========================

def parse_size(text):
    text = text.lower().replace(" ", "")
    if "gb" in text:
        return float(text.replace("gb","")) * 1024
    if "mb" in text:
        return float(text.replace("mb",""))
    return 0

def parse_date(text):
    try:
        return datetime.strptime(text.strip(), "%d/%m/%Y").timestamp()
    except:
        return 0

def extract_code(text):
    match = re.search(r'([A-Z0-9]{2,10}-\d{2,7})', text.upper())
    return match.group(1) if match else None

# =========================
# DB
# =========================

def save_best(actor_name, data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT id FROM downloads WHERE code=?", (data["code"],))
    if c.fetchone():
        conn.close()
        return

    c.execute("""
    INSERT INTO downloads
    (actor_name, code, movie_url, torrent_url, size, seeds, date_ts, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        actor_name,
        data["code"],
        data["movie_url"],
        data["download"],
        data["size"],
        data["seeds"],
        data["date_ts"],
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()

# =========================
# IJAV LOGIC (NEW)
# =========================

def crawl_movie_ijav(movie_url):
    try:
        r = requests.get(movie_url, headers=HEADERS, timeout=20)
    except:
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    torrents = []

    for row in soup.find_all("tr"):
        text = row.get_text(" ", strip=True)

        if not re.search(r'#\d+', text):
            continue

        size_match = re.search(r'([\d\.]+\s?(GB|MB))', text, re.I)
        if not size_match:
            continue

        date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
        seeds_match = re.search(r'Seeds\s*(\d+)', text)

        a = row.find("a", href=True)
        if not a or "/download/" not in a["href"]:
            continue

        torrents.append({
            "size": parse_size(size_match.group(1)),
            "seeds": int(seeds_match.group(1)) if seeds_match else 0,
            "date_ts": parse_date(date_match.group(1)) if date_match else 0,
            "download": urljoin(movie_url, a["href"])
        })

    if not torrents:
        return None

    torrents.sort(key=lambda x: (x["date_ts"], x["size"], x["seeds"]), reverse=True)
    return torrents[0]

def crawl_actor_ijav(actor_name, actor_url):
    print(f"\n🔵 IJAV ACTOR: {actor_name}")

    try:
        r = requests.get(actor_url, headers=HEADERS, timeout=20)
    except:
        print("  ⚠ Cannot load actor page")
        return

    soup = BeautifulSoup(r.text, "html.parser")
    movies = soup.find_all("div", class_="video-item")

    for m in movies:
        a = m.find("a", href=True)
        if not a or "/movie/" not in a["href"]:
            continue

        movie_url = urljoin(actor_url, a["href"])
        code = extract_code(movie_url)
        if not code:
            continue

        best = crawl_movie_ijav(movie_url)
        if not best:
            continue

        best["code"] = code
        best["movie_url"] = movie_url

        print(f"  ✔ {code} | {round(best['size'],1)}MB | Seeds:{best['seeds']}")
        save_best(actor_name, best)

# =========================
# ONEJAV LOGIC (OLD - DOWNLOAD TORRENT)
# =========================

def crawl_actor_onejav(actor_name, actor_url):
    print(f"\n🟢 ONEJAV ACTOR: {actor_name}")

    try:
        r = requests.get(actor_url, headers=HEADERS, timeout=20)
    except:
        print("  ⚠ Cannot load actor page")
        return

    soup = BeautifulSoup(r.text, "html.parser")
    movie_links = []

    for a in soup.find_all("a", href=True):
        if "/movie/" in a["href"]:
            full = urljoin(actor_url, a["href"])
            if full not in movie_links:
                movie_links.append(full)

    print(f"  Movies found: {len(movie_links)}")

    for movie_url in movie_links:
        try:
            r = requests.get(movie_url, headers=HEADERS, timeout=20)
        except:
            continue

        soup = BeautifulSoup(r.text, "html.parser")

        download_link = None
        for a in soup.find_all("a", href=True):
            if "/torrent/" in a["href"] and "download" in a["href"]:
                download_link = urljoin(movie_url, a["href"])
                break

        if not download_link:
            continue

        try:
            torrent_res = requests.get(download_link, headers=HEADERS, timeout=30)
            metadata = bencodepy.decode(torrent_res.content)
            info = metadata[b'info']
            torrent_name = info[b'name'].decode(errors="ignore")
            code = extract_code(torrent_name)
        except:
            continue

        if not code:
            continue

        print(f"  ✔ {code}")

        save_best(actor_name, {
            "code": code,
            "movie_url": movie_url,
            "download": download_link,
            "size": 0,
            "seeds": 0,
            "date_ts": 0
        })

# =========================
# MAIN
# =========================

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, url FROM actors")
    actors = c.fetchall()
    conn.close()

    print("TOTAL ACTORS:", len(actors))

    for name, url in actors:
        if "ijavtorrent.com" in url:
            crawl_actor_ijav(name, url)
        elif "onejav.com" in url:
            crawl_actor_onejav(name, url)

    print("\n✅ HYBRID CRAWL DONE")

if __name__ == "__main__":
    main()

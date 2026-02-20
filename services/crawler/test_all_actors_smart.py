import sqlite3
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from datetime import datetime

DB_PATH = "/app/data/crawler.db"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def parse_size(text):
    text = text.lower().replace(" ", "")
    if "gb" in text:
        return float(text.replace("gb","")) * 1024
    if "mb" in text:
        return float(text.replace("mb",""))
    return 0

def parse_date(text):
    try:
        return datetime.strptime(text.strip(), "%d/%m/%Y")
    except:
        return datetime.min

def extract_int(text):
    try:
        return int(text)
    except:
        return 0

def extract_code(text):
    match = re.search(r'([A-Z]{2,10}-\d{2,6})', text.upper())
    return match.group(1) if match else None

def crawl_movie(movie_url):
    r = requests.get(movie_url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    torrents = []

    for row in soup.find_all("tr"):
        text = row.get_text(" ", strip=True)

        id_match = re.search(r'#(\d+)', text)
        size_match = re.search(r'([\d\.]+\s?(GB|MB))', text, re.I)
        date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
        seeds_match = re.search(r'Seeds\s+(\d+)', text)

        if not (id_match and size_match):
            continue

        a = row.find("a", href=True)
        if not a or "/download/" not in a["href"]:
            continue

        torrents.append({
            "id": id_match.group(1),
            "size": parse_size(size_match.group(1)),
            "date": parse_date(date_match.group(1)) if date_match else datetime.min,
            "seeds": extract_int(seeds_match.group(1)) if seeds_match else 0,
            "download": urljoin(movie_url, a["href"])
        })

    if not torrents:
        return None

    torrents_sorted = sorted(
        torrents,
        key=lambda x: (x["date"], x["size"], x["seeds"]),
        reverse=True
    )

    return torrents_sorted[0]

def test_actor(name, url):
    print("\n====================================================")
    print("🧑 ACTOR:", name)
    print("URL:", url)

    r = requests.get(url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    movie_links = []

    for a in soup.find_all("a", href=True):
        if "/movie/" in a["href"]:
            full = urljoin(url, a["href"])
            if full not in movie_links:
                movie_links.append(full)

    print("Movies found:", len(movie_links))

    valid = 0

    for movie in movie_links:
        best = crawl_movie(movie)
        if best:
            valid += 1
            print("--------------------------------------------------")
            print("MOVIE:", movie)
            print("BEST SIZE (MB):", round(best["size"],1))
            print("SEEDS:", best["seeds"])
            print("DATE:", best["date"].date())
            print("DOWNLOAD:", best["download"])

    print("✅ VALID MOVIES:", valid)

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, url FROM actors")
    actors = c.fetchall()
    conn.close()

    print("TOTAL ACTORS:", len(actors))

    for name, url in actors:
        if "ijavtorrent.com" not in url:
            print("\nSkipping non-ijav actor:", name)
            continue
        test_actor(name, url)

if __name__ == "__main__":
    main()

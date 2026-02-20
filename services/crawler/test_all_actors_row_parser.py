import requests
import sqlite3
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import time

DB_PATH = "/app/data/crawler.db"
HEADERS = {"User-Agent": "Mozilla/5.0"}

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

def crawl_movie(movie_url):
    r = requests.get(movie_url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    torrents = []

    rows = soup.find_all("tr")

    for row in rows:
        text = row.get_text(" ", strip=True)

        if not re.search(r'#\d+', text):
            continue

        a = row.find("a", href=True)
        if not a or "/download/" not in a["href"]:
            continue

        match = re.search(r'([\d\.]+\s?(GB|MB))', text, re.I)
        if not match:
            continue

        size_value = parse_size(match.group(1))

        torrents.append({
            "size": size_value,
            "download": urljoin(movie_url, a["href"])
        })

    if not torrents:
        return None

    return max(torrents, key=lambda x: x["size"])

def crawl_actor(name, actress_url):
    print("\n====================================================")
    print("ACTOR:", name)
    print("URL:", actress_url)

    r = requests.get(actress_url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    movie_links = []

    for a in soup.find_all("a", href=True):
        if "/movie/" in a["href"]:
            full = urljoin(actress_url, a["href"])
            if full not in movie_links:
                movie_links.append(full)

    print("Movies found:", len(movie_links))

    total_valid = 0

    for movie in movie_links:
        try:
            code = extract_code(movie)
            if not code:
                continue

            largest = crawl_movie(movie)
            if not largest:
                continue

            print("--------------------------------------------------")
            print("CODE:", code)
            print("LARGEST SIZE (MB):", round(largest["size"],2))
            print("DOWNLOAD:", largest["download"])

            total_valid += 1
            time.sleep(0.2)

        except Exception as e:
            print("ERROR:", e)

    print("✅ VALID MOVIES:", total_valid)

def main():
    actors = get_actors()
    print("TOTAL ACTORS:", len(actors))

    for name, url in actors:
        if "ijavtorrent" not in url:
            continue
        crawl_actor(name, url)

if __name__ == "__main__":
    main()

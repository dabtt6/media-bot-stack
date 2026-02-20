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
    try:
        if "gb" in text:
            return float(text.replace("gb","")) * 1024
        if "mb" in text:
            return float(text.replace("mb",""))
    except:
        return 0
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

def crawl_movie_page(movie_url):
    r = requests.get(movie_url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    torrents = []

    for row in soup.find_all("tr"):
        download = row.find("a", href=True)
        if not download:
            continue

        if "/download/" not in download["href"]:
            continue

        size_td = row.find("td")
        size_text = row.get_text(" ", strip=True)

        size_match = re.search(r'([\d\.]+\s?(GB|MB))', size_text, re.I)
        if not size_match:
            continue

        size_value = parse_size(size_match.group(1))

        if size_value > 0:
            torrents.append({
                "size": size_value,
                "download": urljoin(movie_url, download["href"])
            })

    return torrents

def crawl_actor(name, actress_url):
    print("\n🧑 ACTOR:", name)
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
            torrents = crawl_movie_page(movie)
            if not torrents:
                continue

            # lấy largest
            largest = max(torrents, key=lambda x: x["size"])

            # lấy code từ movie url
            code = extract_code(movie)

            print("--------------------------------------------------")
            print("CODE:", code)
            print("SIZE (MB):", round(largest["size"],2))
            print("DOWNLOAD:", largest["download"])

            total_valid += 1
            time.sleep(0.5)

        except Exception as e:
            print("Error movie:", e)

    print("\n✅ VALID (largest only):", total_valid)

def main():
    actors = get_actors()
    for name, url in actors:
        crawl_actor(name, url)
        break  # test 1 actor trước

if __name__ == "__main__":
    main()

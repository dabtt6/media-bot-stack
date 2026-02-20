import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0"}
TEST_URL = "https://ijavtorrent.com/movie/start-046-168335"

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

def crawl_movie(movie_url):
    print("Testing movie:", movie_url)
    r = requests.get(movie_url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    torrents = []

    rows = soup.find_all("tr")

    for row in rows:
        text = row.get_text(" ", strip=True)

        id_match = re.search(r'#(\d+)', text)
        if not id_match:
            continue

        size_match = re.search(r'([\d\.]+\s?(GB|MB))', text, re.I)
        if not size_match:
            continue

        date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
        seeds_match = re.search(r'Seeds\s+(\d+)', text)
        leech_match = re.search(r'Leechs?\s+(\d+)', text)

        a = row.find("a", href=True)
        if not a or "/download/" not in a["href"]:
            continue

        torrent = {
            "id": id_match.group(1),
            "size": parse_size(size_match.group(1)),
            "date": parse_date(date_match.group(1)) if date_match else datetime.min,
            "seeds": extract_int(seeds_match.group(1)) if seeds_match else 0,
            "leechs": extract_int(leech_match.group(1)) if leech_match else 0,
            "download": urljoin(movie_url, a["href"])
        }

        torrents.append(torrent)

    print("\nAll torrents found:")
    for t in torrents:
        print(f"ID:{t['id']} | {round(t['size'],1)} MB | Seeds:{t['seeds']} | Date:{t['date'].date()}")

    if not torrents:
        print("No torrents found")
        return

    # SMART SORT
    torrents_sorted = sorted(
        torrents,
        key=lambda x: (x["date"], x["size"], x["seeds"]),
        reverse=True
    )

    best = torrents_sorted[0]

    print("\n🎯 SELECTED BEST:")
    print(f"ID:{best['id']}")
    print(f"SIZE:{round(best['size'],1)} MB")
    print(f"SEEDS:{best['seeds']}")
    print(f"DATE:{best['date'].date()}")
    print(f"DOWNLOAD:{best['download']}")

if __name__ == "__main__":
    crawl_movie(TEST_URL)

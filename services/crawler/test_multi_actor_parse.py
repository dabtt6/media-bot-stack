import requests
import sqlite3
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}
DB_PATH = "/app/data/crawler.db"   # DB trong container

def parse_size(text):
    text = text.lower().replace(" ", "")
    if "gb" in text:
        return float(text.replace("gb", "")) * 1024
    if "mb" in text:
        return float(text.replace("mb", ""))
    return 0

def extract_code(title):
    title = title.strip().upper()
    match = re.match(r'^([A-Z]+)[\s\-]?(\d+)', title)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return None

def crawl_actor(name, url):
    print("\n" + "="*80)
    print(f"🎭 ACTOR: {name}")
    print("URL:", url)

    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
    except Exception as e:
        print("❌ HTTP ERROR:", e)
        return

    soup = BeautifulSoup(r.text, "html.parser")
    cards = soup.find_all("div", class_="video-item")

    print("Found cards:", len(cards))

    valid = 0

    for card in cards:
        name_div = card.find("div", class_="name")
        if not name_div:
            continue

        title = name_div.get_text(strip=True)
        code = extract_code(title)

        download_link = None
        for a in card.find_all("a", href=True):
            if "/download/" in a["href"]:
                download_link = urljoin(url, a["href"])
                break

        size_value = 0
        for td in card.find_all("td"):
            text = td.get_text(strip=True)
            if "GB" in text.upper() or "MB" in text.upper():
                size_value = parse_size(text)

        if download_link and size_value > 0:
            print(f"{code} | {round(size_value,2)} MB")
            valid += 1

    print("✅ VALID TORRENTS:", valid)


def main():
    print("📦 Loading actors from DB...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name, url FROM actors")
    actors = cursor.fetchall()

    conn.close()

    print("Total actors:", len(actors))

    for name, url in actors:
        crawl_actor(name, url)


if __name__ == "__main__":
    main()

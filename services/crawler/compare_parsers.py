import sqlite3
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

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

# ---------------- OLD PARSER ----------------
def parse_old(movie_url):
    r = requests.get(movie_url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    largest = 0
    best_dl = None

    for td in soup.find_all("td"):
        text = td.get_text(strip=True)
        if "GB" in text.upper() or "MB" in text.upper():
            size = parse_size(text)
            link = td.find_parent("tr").find("a", href=True)
            if link and "/download/" in link["href"]:
                if size > largest:
                    largest = size
                    best_dl = urljoin(movie_url, link["href"])

    return largest, best_dl

# ---------------- NEW PARSER (#ID BASED) ----------------
def parse_new(movie_url):
    r = requests.get(movie_url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    largest = 0
    best_dl = None

    for row in soup.find_all("tr"):
        text = row.get_text(" ", strip=True)

        if not re.search(r'#\d+', text):
            continue

        match = re.search(r'([\d\.]+\s?(GB|MB))', text, re.I)
        if not match:
            continue

        size = parse_size(match.group(1))

        a = row.find("a", href=True)
        if not a or "/download/" not in a["href"]:
            continue

        if size > largest:
            largest = size
            best_dl = urljoin(movie_url, a["href"])

    return largest, best_dl

# ---------------- MAIN ----------------
def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT name, url FROM actors")
    actors = c.fetchall()

    for name, actor_url in actors:
        if "ijavtorrent" not in actor_url:
            continue

        print("\n===============================")
        print("ACTOR:", name)
        print("===============================")

        r = requests.get(actor_url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")

        cards = soup.find_all("div", class_="video-item")

        for card in cards:
            name_div = card.find("div", class_="name")
            if not name_div:
                continue

            a = name_div.find("a")
            if not a:
                continue

            movie_url = urljoin(actor_url, a["href"])
            title = a.get_text(strip=True)
            code = extract_code(title)

            old_size, old_dl = parse_old(movie_url)
            new_size, new_dl = parse_new(movie_url)

            if old_size != new_size:
                print("\n⚠ SIZE MISMATCH:", code)
                print("OLD:", old_size, old_dl)
                print("NEW:", new_size, new_dl)

    conn.close()

if __name__ == "__main__":
    main()

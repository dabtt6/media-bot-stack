import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sqlite3
import re
import time

HEADERS = {"User-Agent": "Mozilla/5.0"}
DB = "/app/data/crawler_test.db"

# ========================
# DB INIT
# ========================

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS downloads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor_name TEXT,
        code TEXT,
        torrent_url TEXT,
        size REAL,
        seeds INTEGER,
        source TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()

def save(actor, code, url, size, seeds, source):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    INSERT INTO downloads (actor_name, code, torrent_url, size, seeds, source, created_at)
    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
    """, (actor, code, url, size, seeds, source))

    conn.commit()
    conn.close()

# ========================
# IJAV LOGIC (NEW)
# ========================

def parse_size(text):
    text = text.lower().replace(" ", "")
    if "gb" in text:
        return float(text.replace("gb", "")) * 1024
    if "mb" in text:
        return float(text.replace("mb", ""))
    return 0

def crawl_ijav(actor, url):
    print(f"\n🔵 IJAV ACTOR: {actor}")
    r = requests.get(url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    movies = soup.find_all("a", href=True)
    movie_links = []

    for a in movies:
        if "/movie/" in a["href"]:
            movie_links.append(urljoin(url, a["href"]))

    movie_links = list(set(movie_links))
    print("Movies:", len(movie_links))

    for m in movie_links:
        try:
            rm = requests.get(m, headers=HEADERS, timeout=20)
            sm = BeautifulSoup(rm.text, "html.parser")

            trs = sm.find_all("tr")
            best = None

            for tr in trs:
                text = tr.get_text(" ", strip=True)
                if not text.startswith("#"):
                    continue

                parts = text.split()
                code = None
                size = 0
                seeds = 0

                # extract code
                title = sm.title.string if sm.title else ""
                match = re.search(r'([A-Z0-9\-]+)', title.upper())
                if match:
                    code = match.group(1)

                # size
                for p in parts:
                    if "gb" in p.lower() or "mb" in p.lower():
                        size = parse_size(p)

                # seeds
                if "Seeds" in parts:
                    try:
                        idx = parts.index("Seeds")
                        seeds = int(parts[idx+1])
                    except:
                        pass

                download = tr.find("a", href=True)
                if not download:
                    continue

                dl_url = urljoin(m, download["href"])

                if not best or size > best["size"]:
                    best = {
                        "code": code,
                        "url": dl_url,
                        "size": size,
                        "seeds": seeds
                    }

            if best:
                print(f"  ✔ {best['code']} | {round(best['size'],1)}MB | Seeds:{best['seeds']}")
                save(actor, best["code"], best["url"], best["size"], best["seeds"], "ijav")

        except Exception as e:
            print("  Error movie:", e)

# ========================
# ONEJAV LOGIC (NEW HTML STRUCTURE)
# ========================

def crawl_onejav(actor, url):
    print(f"\n🟢 ONEJAV ACTOR: {actor}")

    r = requests.get(url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    cards = soup.find_all("div", class_="card-content")
    print("Cards:", len(cards))

    for card in cards:
        title = card.find("h5", class_="title")
        if not title:
            continue

        a = title.find("a")
        span = title.find("span")

        if not a or not span:
            continue

        code = a.get_text(strip=True).upper()
        size = parse_size(span.get_text(strip=True))

        btn = card.find("a", class_="button is-primary")
        if not btn:
            continue

        dl = urljoin(url, btn["href"])

        print(f"  ✔ {code} | {round(size,1)}MB")
        save(actor, code, dl, size, 0, "onejav")

# ========================
# LOAD ACTORS FROM MAIN DB
# ========================

def load_actors():
    conn = sqlite3.connect("/app/data/crawler.db")
    c = conn.cursor()
    c.execute("SELECT name, url FROM actors")
    rows = c.fetchall()
    conn.close()
    return rows

# ========================
# MAIN
# ========================

def main():
    init_db()
    actors = load_actors()

    print("TOTAL ACTORS:", len(actors))

    for name, url in actors:
        if "ijavtorrent" in url:
            crawl_ijav(name, url)
        elif "onejav" in url:
            crawl_onejav(name, url)

        time.sleep(1)

    print("\n✅ TEST DONE")
    print("DB:", DB)

if __name__ == "__main__":
    main()

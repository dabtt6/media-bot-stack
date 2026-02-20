import requests
from bs4 import BeautifulSoup
import sqlite3
import re
from urllib.parse import urljoin
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0"}
DB_PATH = "/docker/media-stack/data/crawler/crawler.db"

# =========================
# EXTRACT CODE PRO
# =========================
def extract_code(text):
    text = text.upper()

    m = re.search(r'([A-Z]{2,10}-\d{2,7})', text)
    if m:
        return m.group(1)

    m = re.search(r'PPV\s?(\d{5,9})', text)
    if m:
        return f"PPV-{m.group(1)}"

    return None

# =========================
# PARSE SIZE
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

# =========================
# IJAV LOGIC
# =========================
def crawl_ijav(actor, url):
    print(f"\n🔵 IJAV ACTOR: {actor}")
    r = requests.get(url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    movies = [
        urljoin(url, a["href"])
        for a in soup.find_all("a", href=True)
        if "/movie/" in a["href"]
    ]

    print("Movies found:", len(movies))

    for m in movies[:5]:  # test 5 movie đầu cho nhẹ
        try:
            rm = requests.get(m, headers=HEADERS, timeout=20)
            sm = BeautifulSoup(rm.text, "html.parser")

            best = None
            code = None

            title = sm.find("title")
            if title:
                code = extract_code(title.text)

            for tr in sm.find_all("tr"):
                row_text = tr.get_text(" ", strip=True)

                if "#" not in row_text:
                    continue

                size = 0
                seeds = 0
                date_ts = 0
                download = None

                for td in tr.find_all("td"):
                    txt = td.get_text(strip=True)

                    if "GB" in txt.upper() or "MB" in txt.upper():
                        size = parse_size(txt)

                    if "Seeds" in txt:
                        s = re.search(r'Seeds\s*(\d+)', row_text)
                        if s:
                            seeds = int(s.group(1))

                    if re.match(r"\d{2}/\d{2}/\d{4}", txt):
                        date_ts = parse_date(txt)

                for a in tr.find_all("a", href=True):
                    if "/download/" in a["href"]:
                        download = urljoin(url, a["href"])

                if size > 0 and download:
                    score = (size, seeds, date_ts)
                    if not best or score > best[0]:
                        best = (score, size, seeds, download)

            if best and code:
                print(f"  ✔ {code} | {round(best[1],1)}MB | Seeds:{best[2]}")

        except Exception as e:
            print("  Error movie:", e)

# =========================
# ONEJAV LOGIC
# =========================
def crawl_onejav(actor, url):
    print(f"\n🟢 ONEJAV ACTOR: {actor}")

    r = requests.get(url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    links = [
        urljoin("https://onejav.com", a["href"])
        for a in soup.find_all("a", href=True)
        if "/torrent/" in a["href"] and "/download/" in a["href"]
    ]

    print("Download links found:", len(links))

    for l in links[:10]:  # test 10 link đầu
        code = extract_code(l)
        if code:
            print(f"  ✔ {code} | {l}")

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
        if "ijavtorrent" in url:
            crawl_ijav(name, url)
        elif "onejav" in url:
            crawl_onejav(name, url)

    print("\nDONE.")

if __name__ == "__main__":
    main()

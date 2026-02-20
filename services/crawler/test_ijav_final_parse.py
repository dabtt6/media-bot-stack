import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}
TEST_URL = "https://ijavtorrent.com/actress/yuuka-minase-2310/"

def parse_size(text):
    text = text.lower().replace(" ", "")
    if "gb" in text:
        return float(text.replace("gb", "")) * 1024
    if "mb" in text:
        return float(text.replace("mb", ""))
    return 0

def extract_code(text):
    match = re.search(r'([A-Z]{2,10}-\d{2,6})', text.upper())
    return match.group(1) if match else None

def crawl():
    print("🔎 Crawling:", TEST_URL)

    r = requests.get(TEST_URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    cards = soup.find_all("div", class_="video-item")

    print("Found cards:", len(cards))

    for card in cards:
        # CODE
        name_div = card.find("div", class_="name")
        if not name_div:
            continue

        title = name_div.get_text(strip=True)
        code = extract_code(title)

        # DOWNLOAD
        download_link = None
        for a in card.find_all("a", href=True):
            if "/download/" in a["href"]:
                download_link = urljoin(TEST_URL, a["href"])
                break

        # SIZE
        size_value = 0
        for td in card.find_all("td"):
            text = td.get_text(strip=True)
            if "GB" in text.upper() or "MB" in text.upper():
                size_value = parse_size(text)

        if code and size_value > 0:
            print("="*60)
            print("CODE:", code)
            print("SIZE (MB):", round(size_value,2))
            print("DOWNLOAD:", download_link)

if __name__ == "__main__":
    crawl()

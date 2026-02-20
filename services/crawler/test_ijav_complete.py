import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {"User-Agent": "Mozilla/5.0"}
TEST_URL = "https://ijavtorrent.com/actress/yuuka-minase-2310/"

def parse_size(text):
    text = text.lower().replace(" ", "")
    if "gb" in text:
        return float(text.replace("gb", "")) * 1024
    if "mb" in text:
        return float(text.replace("mb", ""))
    return 0

import re

def extract_code(title):
    """
    Chuẩn hóa code:
    ppv 1317993  -> PPV-1317993
    ebod-205     -> EBOD-205
    sone 983     -> SONE-983
    """
    title = title.strip().upper()
    match = re.match(r"^([A-Z]+)[\s\-]?(\d+)", title)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return None
    title = title.replace(" ", "-")
    return title

def crawl():
    print("🔎 Crawling:", TEST_URL)

    r = requests.get(TEST_URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    cards = soup.find_all("div", class_="video-item")

    print("Found cards:", len(cards))

    total = 0

    for card in cards:

        # === CODE ===
        name_div = card.find("div", class_="name")
        if not name_div:
            continue

        title = name_div.get_text(strip=True)
        code = extract_code(title)

        # === DOWNLOAD LINK ===
        download_link = None
        for a in card.find_all("a", href=True):
            if "/download/" in a["href"]:
                download_link = urljoin(TEST_URL, a["href"])
                break

        # === SIZE ===
        size_value = 0
        for td in card.find_all("td"):
            text = td.get_text(strip=True)
            if "GB" in text.upper() or "MB" in text.upper():
                size_value = parse_size(text)

        # === VALID TORRENT ===
        if download_link and size_value > 0:
            print("="*60)
            print("CODE:", code)
            print("SIZE (MB):", round(size_value,2))
            print("DOWNLOAD:", download_link)
            total += 1

    print("\n✅ TOTAL VALID TORRENTS:", total)

if __name__ == "__main__":
    crawl()

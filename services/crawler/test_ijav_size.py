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

    rows = soup.find_all("tr")

    found = 0

    for row in rows:
        download_link = None
        size_value = 0
        code = None

        # download link
        a = row.find("a", href=True)
        if a and "/download/" in a["href"]:
            download_link = urljoin(TEST_URL, a["href"])
            code = extract_code(a.get_text())

        # size cell
        tds = row.find_all("td")
        for td in tds:
            text = td.get_text(strip=True)
            if "GB" in text.upper() or "MB" in text.upper():
                size_value = parse_size(text)

        if download_link and size_value > 0:
            print("="*60)
            print("CODE:", code)
            print("SIZE (MB):", round(size_value,2))
            print("DOWNLOAD:", download_link)
            found += 1

    print("\n✅ TOTAL FOUND:", found)

if __name__ == "__main__":
    crawl()

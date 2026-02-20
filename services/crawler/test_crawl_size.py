import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}

TEST_URL = "https://onejav.com/actress/yuuka-minase"  # đổi theo actor bạn muốn test


def parse_size(size_text):
    size_text = size_text.lower().replace(" ", "")
    if "gb" in size_text:
        return float(size_text.replace("gb", "")) * 1024
    if "mb" in size_text:
        return float(size_text.replace("mb", ""))
    return 0


def extract_code(text):
    match = re.search(r'([A-Z]{2,10}-\d{2,6})', text.upper())
    return match.group(1) if match else None


def test_crawl():
    print("🔎 Crawling:", TEST_URL)

    r = requests.get(TEST_URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    rows = soup.find_all("tr")

    found = 0

    for row in rows:
        magnet_link = None
        download_link = None
        size_value = 0

        # lấy magnet
        a_tags = row.find_all("a", href=True)
        for a in a_tags:
            href = a["href"]
            if href.startswith("magnet:?"):
                magnet_link = href
            if "/download/" in href:
                download_link = urljoin(TEST_URL, href)

        # lấy size
        tds = row.find_all("td")
        for td in tds:
            text = td.get_text(strip=True).lower()
            if "gb" in text or "mb" in text:
                size_value = parse_size(text)

        if magnet_link and size_value > 0:
            code = extract_code(magnet_link)

            print("=" * 60)
            print("CODE:", code)
            print("SIZE (MB):", round(size_value, 2))
            print("DOWNLOAD:", download_link)
            print("MAGNET:", magnet_link[:80], "...")

            found += 1

    print("\n✅ TOTAL VALID TORRENTS FOUND:", found)


if __name__ == "__main__":
    test_crawl()

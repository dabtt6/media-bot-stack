import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}
TEST_MOVIE = "https://ijavtorrent.com/movie/start-046-168335"

def parse_size(text):
    text = text.lower().replace(" ", "")
    if "gb" in text:
        return float(text.replace("gb","")) * 1024
    if "mb" in text:
        return float(text.replace("mb",""))
    return 0

print("Testing movie:", TEST_MOVIE)

r = requests.get(TEST_MOVIE, headers=HEADERS, timeout=30)
soup = BeautifulSoup(r.text, "html.parser")

torrents = []

for a in soup.find_all("a", href=True):
    if "/download/" not in a["href"]:
        continue

    # block torrent thường nằm trong div col-md-6
    block = a.find_parent("div", class_="col-md-6")
    if not block:
        continue

    text = block.get_text(" ", strip=True)

    size_match = re.search(r'([\d\.]+\s?(GB|MB))', text, re.I)
    if not size_match:
        continue

    size = parse_size(size_match.group(1))

    torrents.append({
        "size": size,
        "download": urljoin(TEST_MOVIE, a["href"])
    })

print("\nAll torrents found:")
for t in torrents:
    print("SIZE:", t["size"], "MB")
    print("DL:", t["download"])
    print("-"*40)

if torrents:
    largest = max(torrents, key=lambda x: x["size"])
    print("\nLARGEST:", largest["size"], "MB")

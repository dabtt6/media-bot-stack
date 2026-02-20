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

# tìm tất cả icon size trước
for icon in soup.find_all("i", class_=lambda x: x and "weight-hanging" in x):

    parent_row = icon.find_parent("div", class_="row")
    if not parent_row:
        continue

    # tìm download link trong cùng row
    download = parent_row.find("a", href=True)
    if not download or "/download/" not in download["href"]:
        continue

    size_text = icon.parent.get_text(strip=True)
    size_match = re.search(r'([\d\.]+\s?(GB|MB))', size_text, re.I)
    if not size_match:
        continue

    size_value = parse_size(size_match.group(1))

    torrents.append({
        "size": size_value,
        "download": urljoin(TEST_MOVIE, download["href"])
    })

print("\nAll torrents found:")
for t in torrents:
    print("SIZE:", t["size"], "MB")
    print("DL:", t["download"])
    print("-"*40)

if torrents:
    largest = max(torrents, key=lambda x: x["size"])
    print("\nLARGEST:", largest["size"], "MB")

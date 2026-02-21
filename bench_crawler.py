import requests
import time
from concurrent.futures import ThreadPoolExecutor

BASE = "https://ijavtorrent.com/actress/remu-suzumori-10857"

MAX_PAGE = 10
THREADS = 50
REQ_PER_PAGE = 100

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

def build_url(page):
    if page == 1:
        return BASE
    return f"{BASE}?page={page}"

def fetch(url):
    try:
        r = session.get(url, timeout=10)
        return r.status_code
    except:
        return 0

urls = []

for page in range(1, MAX_PAGE + 1):
    page_url = build_url(page)
    for _ in range(REQ_PER_PAGE):
        urls.append(page_url)

start = time.time()

with ThreadPoolExecutor(max_workers=THREADS) as executor:
    results = list(executor.map(fetch, urls))

end = time.time()

success = results.count(200)

print("Pages:", MAX_PAGE)
print("Threads:", THREADS)
print("Total Requests:", len(urls))
print("Success:", success)
print("Time:", round(end - start, 2))
print("Req/sec:", round(len(urls) / (end - start), 2))
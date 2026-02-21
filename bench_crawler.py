# -*- coding: utf-8 -*-

import requests
import time
from concurrent.futures import ThreadPoolExecutor

ACTORS = [
    "remu-suzumori-10857",
    "yuuka-minase-2310",
    "rei-kamiki-11034",
    "mirei-shinonome-11890",
    "mika-azuma-13345",
    "sayuri-hayama-9981",
    "melody-marks-10293",
    "nakamori-nanami-11233",
    "shidou-rui-11201",
    "fukuda-yua-11302",
]

MAX_PAGE = 10
THREADS = 70  # test 50 / 70 / 80

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

def build_urls():
    urls = []
    for actor in ACTORS:
        base = f"https://ijavtorrent.com/actress/{actor}"
        for page in range(1, MAX_PAGE + 1):
            if page == 1:
                urls.append(base)
            else:
                urls.append(base + f"?page={page}")
    return urls

def fetch(url):
    try:
        r = session.get(url, timeout=10)
        return r.status_code
    except:
        return 0

urls = build_urls()

start = time.time()

with ThreadPoolExecutor(max_workers=THREADS) as executor:
    results = list(executor.map(fetch, urls))

end = time.time()

success = results.count(200)

print("\n==========================")
print("Threads:", THREADS)
print("Total Requests:", len(urls))
print("Success:", success)
print("Time:", round(end-start, 2))
print("Req/sec:", round(len(urls)/(end-start), 2))
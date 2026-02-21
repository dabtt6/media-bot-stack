# -*- coding: utf-8 -*-

import asyncio
import aiohttp
import time
import random

# ================= CONFIG =================

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

MIN_CONCURRENT = 30
MAX_CONCURRENT = 80
START_CONCURRENT = 50

TARGET_SUCCESS = 0.95
LOW_THRESHOLD = 0.80

BATCH_SLEEP = 5

concurrent = START_CONCURRENT

# ================= URL BUILD =================

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

# ================= FETCH =================

async def fetch(session, url):
    try:
        async with session.get(url, timeout=10) as resp:
            await asyncio.sleep(random.uniform(0.05, 0.15))
            return resp.status
    except:
        return 0

# ================= RUN BATCH =================

async def run_batch():

    global concurrent

    urls = build_urls()

    connector = aiohttp.TCPConnector(limit=concurrent, ssl=False)
    timeout = aiohttp.ClientTimeout(total=15)

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        headers={"User-Agent": "Mozilla/5.0"}
    ) as session:

        tasks = [fetch(session, url) for url in urls]

        start = time.time()
        results = await asyncio.gather(*tasks)
        end = time.time()

        success = results.count(200)
        rate = success / len(results)

        print("\n==========================")
        print(f"Concurrent: {concurrent}")
        print(f"Total Requests: {len(results)}")
        print(f"Success: {success} ({round(rate*100,2)}%)")
        print("Time:", round(end-start, 2))
        print("Req/sec:", round(len(results)/(end-start), 2))

        # ===== Adaptive Logic =====
        if rate > TARGET_SUCCESS and concurrent < MAX_CONCURRENT:
            concurrent += 5
            print("? Increasing concurrency")
        elif rate < LOW_THRESHOLD and concurrent > MIN_CONCURRENT:
            concurrent -= 10
            print("? Decreasing concurrency")

        concurrent = max(MIN_CONCURRENT, min(MAX_CONCURRENT, concurrent))

# ================= MAIN LOOP =================

async def main():
    print("Multi-Actor Adaptive Crawler Started")
    while True:
        await run_batch()
        await asyncio.sleep(BATCH_SLEEP)

asyncio.run(main())
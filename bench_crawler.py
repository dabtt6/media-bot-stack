# -*- coding: utf-8 -*-

import asyncio
import aiohttp
import time
import random

BASE = "https://ijavtorrent.com/actress/remu-suzumori-10857"
MAX_PAGE = 10

MIN_CONCURRENT = 30
MAX_CONCURRENT = 80
START_CONCURRENT = 50

BATCH_SIZE = 200
TARGET_SUCCESS = 0.95

concurrent = START_CONCURRENT


def build_urls():
    urls = []
    for page in range(1, MAX_PAGE + 1):
        if page == 1:
            url = BASE
        else:
            url = BASE + "?page=" + str(page)
        urls.append(url)
    return urls


async def fetch(session, url):
    try:
        async with session.get(url, timeout=10) as resp:
            await asyncio.sleep(random.uniform(0.05, 0.15))
            return resp.status
    except:
        return 0


async def run_batch():

    global concurrent

    urls = build_urls()
    urls = urls * (BATCH_SIZE // len(urls))

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

        print(f"\nConcurrent: {concurrent}")
        print(f"Success: {success}/{len(results)} ({round(rate*100,2)}%)")
        print("Time:", round(end-start, 2))
        print("Req/sec:", round(len(results)/(end-start), 2))

        # Adaptive logic
        if rate > TARGET_SUCCESS and concurrent < MAX_CONCURRENT:
            concurrent += 5
            print("? Increasing concurrency")
        elif rate < 0.8 and concurrent > MIN_CONCURRENT:
            concurrent -= 10
            print("? Decreasing concurrency")

        concurrent = max(MIN_CONCURRENT, min(MAX_CONCURRENT, concurrent))


async def main():
    print("Adaptive crawler started")
    while True:
        await run_batch()
        await asyncio.sleep(5)


asyncio.run(main())
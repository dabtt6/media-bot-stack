# -*- coding: utf-8 -*-

import asyncio
import aiohttp
import time

BASE = "https://ijavtorrent.com/actress/remu-suzumori-10857"

MAX_PAGE = 10
REQ_PER_PAGE = 100
CONCURRENT = 200

def build_url(page):
    if page == 1:
        return BASE
    return BASE + "?page=" + str(page)

urls = []
for page in range(1, MAX_PAGE + 1):
    for _ in range(REQ_PER_PAGE):
        urls.append(build_url(page))

async def fetch(session, url):
    try:
        async with session.get(url, timeout=10) as resp:
            return resp.status
    except:
        return 0

async def run():
    connector = aiohttp.TCPConnector(limit=CONCURRENT, ssl=False)
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

        print("Concurrent:", CONCURRENT)
        print("Total:", len(urls))
        print("Success:", success)
        print("Time:", round(end-start, 2))
        print("Req/sec:", round(len(urls)/(end-start), 2))

asyncio.run(run())
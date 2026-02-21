import requests
import time
from concurrent.futures import ThreadPoolExecutor

URL = "https://ijavtorrent.com/"
THREADS = 100
TOTAL_REQUESTS = 2000

def fetch(i):
    try:
        r = requests.get(URL, timeout=10)
        return r.status_code
    except:
        return 0

start = time.time()

with ThreadPoolExecutor(max_workers=THREADS) as executor:
    results = list(executor.map(fetch, range(TOTAL_REQUESTS)))

end = time.time()

success = results.count(200)

print("Threads:", THREADS)
print("Total:", TOTAL_REQUESTS)
print("Success:", success)
print("Time:", round(end-start,2))
print("Req/sec:", round(TOTAL_REQUESTS/(end-start),2))
import requests, random, time, threading
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TEST_URLS = [
    "https://ijavtorrent.com/movie/start-046-168335",
    "https://ijavtorrent.com/movie/start-488-217895",
    "https://ijavtorrent.com/movie/start-508-216997",
    "https://ijavtorrent.com/movie/start-473-210505"
]

# =========================
# CREATE SAFE SESSION
# =========================
def create_session():
    session = requests.Session()

    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429,500,502,503,504],
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(
        max_retries=retries,
        pool_connections=5,
        pool_maxsize=5
    )

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update({
        "User-Agent": "Mozilla/5.0"
    })

    return session

session = create_session()

# =========================
# SAFE GET
# =========================
def worker(url):
    try:
        time.sleep(random.uniform(0.3,1.0))
        r = session.get(url, timeout=20)
        print("✅ OK:", url, "| Status:", r.status_code, "| Len:", len(r.text))
    except Exception as e:
        print("❌ ERROR:", url, "|", e)

threads = []

print("\n🚀 START TEST THREADS\n")

for url in TEST_URLS:
    t = threading.Thread(target=worker, args=(url,))
    t.start()
    threads.append(t)

for t in threads:
    t.join()

print("\n🎯 TEST DONE\n")

import requests, random, time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
        pool_connections=10,
        pool_maxsize=10
    )

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    })

    return session


# =========================
# SAFE GET WRAPPER
# =========================
def safe_get(session, url, timeout=30):

    # random delay chống ban
    time.sleep(random.uniform(0.4,1.2))

    try:
        r = session.get(url, timeout=timeout)
        r.raise_for_status()
        return r

    except Exception as e:
        print("[SSL RETRY ERROR]", url, e)
        return None

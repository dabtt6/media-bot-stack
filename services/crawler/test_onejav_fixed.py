import requests, re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {"User-Agent":"Mozilla/5.0"}

actors = [
    ("Remu Suzumori","https://onejav.com/actress/Remu%20Suzumori"),
]

def normalize_code(raw):
    raw = raw.upper()
    m = re.match(r'([A-Z]+)(\d+)', raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return raw

def crawl_onejav(actor, url):
    print("\n==============================")
    print("ACTOR:", actor)
    print("==============================")

    r = requests.get(url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    count = 0

    for a in soup.find_all("a", href=True):
        if "/torrent/" in a["href"] and a["href"].endswith(".torrent"):
            full = urljoin(url, a["href"])

            filename = full.split("/")[-1]
            filename = filename.replace(".torrent","")

            # remove prefix
            filename = filename.replace("onejav.com_","")

            code = normalize_code(filename)

            print("✔", code, "|", full)
            count += 1

    print("TOTAL:", count)

for name, url in actors:
    crawl_onejav(name, url)

print("\nDONE.")

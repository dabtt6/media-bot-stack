import requests, re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {"User-Agent":"Mozilla/5.0"}

actors = [
    ("Remu Suzumori","https://onejav.com/actress/Remu%20Suzumori"),
    ("Melody Marks","https://onejav.com/actress/Melody%20Marks"),
]

def extract_code(text):
    m = re.search(r'([A-Z0-9]+-\d+)', text.upper())
    return m.group(1) if m else None

def crawl_onejav(actor, url):
    print("\n==============================")
    print("ACTOR:", actor)
    print("==============================")

    r = requests.get(url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    cards = soup.find_all("div", class_="video-item")
    print("Cards found:", len(cards))

    count = 0

    for card in cards:
        text = card.get_text(" ", strip=True)

        # tìm link download
        dl = None
        for a in card.find_all("a", href=True):
            if "/download/" in a["href"]:
                dl = urljoin(url, a["href"])
                break

        if not dl:
            continue

        code = extract_code(text)

        print("✔", code, "|", dl)
        count += 1

    print("TOTAL DOWNLOAD LINKS:", count)


for name, url in actors:
    crawl_onejav(name, url)

print("\nDONE.")

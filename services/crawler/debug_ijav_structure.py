import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}
TEST_URL = "https://ijavtorrent.com/actress/yuuka-minase-2310/"

r = requests.get(TEST_URL, headers=HEADERS, timeout=30)
soup = BeautifulSoup(r.text, "html.parser")

names = soup.find_all("div", class_="name")

print("Found name blocks:", len(names))

if names:
    block = names[0]
    print("\n--- div.name HTML ---\n")
    print(block.prettify())

    parent = block.parent
    print("\n--- Parent tag ---\n")
    print(parent.name, parent.get("class"))

    print("\n--- Parent HTML snippet ---\n")
    print(parent.prettify()[:1500])

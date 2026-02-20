import requests, re, time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

HEADERS = {"User-Agent":"Mozilla/5.0"}

actors = [
    ('Yuuka Minase','https://ijavtorrent.com/actress/yuuka-minase-2310/'),
    ('Rei Kamiki','https://ijavtorrent.com/actress/rei-kamiki-23668/'),
    ('Remu Suzumori','https://onejav.com/actress/Remu%20Suzumori'),
]

def parse_size(text):
    text=text.lower().replace(' ','')
    if 'gb' in text:
        return float(text.replace('gb',''))*1024
    if 'mb' in text:
        return float(text.replace('mb',''))
    return 0

def parse_date(text):
    try:
        return datetime.strptime(text.strip(), '%d/%m/%Y').timestamp()
    except:
        return 0

def extract_code(text):
    if not text:
        return None
    text = text.upper()

    m = re.search(r'([A-Z]{2,10}-\d{2,6})', text)
    if m:
        return m.group(1)

    m = re.search(r'PPV[\s\-]?(\d{4,7})', text)
    if m:
        return f"PPV-{m.group(1)}"

    return None


def crawl_ijav(actor,url):
    print("\n==============================")
    print("🔵 IJAV:",actor)
    print("==============================")

    r=requests.get(url,headers=HEADERS,timeout=20)
    soup=BeautifulSoup(r.text,'html.parser')

    movie_links=[urljoin(url,a['href']) for a in soup.select('div.name a')]
    print("Movies:",len(movie_links))

    for m in movie_links:
        time.sleep(0.4)
        rm=requests.get(m,headers=HEADERS,timeout=20)
        msoup=BeautifulSoup(rm.text,'html.parser')

        title_tag = msoup.find("title")
        code = None
        if title_tag:
            code = extract_code(title_tag.get_text())
        if not code:
            code = extract_code(m)

        torrents=[]
        for tr in msoup.find_all('tr'):
            text=tr.get_text(" ",strip=True)
            if "#" in text and "Download" in text:

                size_match=re.search(r'(\d+(\.\d+)?)(gb|mb)',text.lower())
                size=parse_size(size_match.group()) if size_match else 0

                seeds_match=re.search(r'Seeds\s*(\d+)',text)
                seeds=int(seeds_match.group(1)) if seeds_match else 0

                date_match=re.search(r'\d{2}/\d{2}/\d{4}',text)
                date=parse_date(date_match.group()) if date_match else 0

                dl=None
                for a in tr.find_all('a',href=True):
                    if '/download/' in a['href']:
                        dl=urljoin(url,a['href'])
                        break

                if size>0 and dl:
                    torrents.append((size,seeds,date,dl))

        if torrents:
            torrents.sort(key=lambda x:(x[2],x[0],x[1]),reverse=True)
            best=torrents[0]
            print(f"✔ {code} | {round(best[0],1)} MB | Seeds: {best[1]}")
        else:
            print(f"✘ {code} | no torrent")


def crawl_onejav(actor,url):
    print("\n==============================")
    print("🟢 ONEJAV:",actor)
    print("==============================")

    r=requests.get(url,headers=HEADERS,timeout=20)
    soup=BeautifulSoup(r.text,'html.parser')

    links=[]
    for a in soup.find_all("a",href=True):
        if "/torrent/" in a['href'] and "/download/" in a['href']:
            links.append(urljoin(url,a['href']))

    print("Torrent links:",len(links))

    for l in links:
        code = extract_code(l)
        print("✔",code,"|",l)


for name,url in actors:
    if "ijavtorrent" in url:
        crawl_ijav(name,url)
    else:
        crawl_onejav(name,url)

print("\nDONE.")

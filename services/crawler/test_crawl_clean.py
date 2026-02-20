import requests, re, time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

HEADERS = {"User-Agent":"Mozilla/5.0"}

actors = [
    ('Yuuka Minase','https://ijavtorrent.com/actress/yuuka-minase-2310/'),
    ('Rei Kamiki','https://ijavtorrent.com/actress/rei-kamiki-23668/'),
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
    m=re.search(r'([A-Z0-9]+-\d+)', text.upper())
    return m.group(1) if m else None

def crawl_ijav(actor,url):
    print("\n==============================")
    print("ACTOR:",actor)
    print("==============================")

    r=requests.get(url,headers=HEADERS,timeout=20)
    soup=BeautifulSoup(r.text,'html.parser')

    movie_links=[]
    for a in soup.select('div.name a'):
        movie_links.append(urljoin(url,a['href']))

    print("Movies found:",len(movie_links))

    for m in movie_links[:5]:
        time.sleep(0.8)
        rm=requests.get(m,headers=HEADERS,timeout=20)
        msoup=BeautifulSoup(rm.text,'html.parser')

        code=extract_code(m)
        rows=msoup.find_all('tr')

        torrents=[]
        for tr in rows:
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
            print("✔",code,"|",round(best[0],1),"MB | Seeds:",best[1])
        else:
            print("✘",code,"| no torrent")

for name,url in actors:
    crawl_ijav(name,url)

print("\nDONE.")

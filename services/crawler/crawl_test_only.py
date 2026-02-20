import requests, re, sqlite3, time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

DB = "/app/data/crawler_test.db"
HEADERS = {"User-Agent":"Mozilla/5.0"}

# ========================
# DB INIT
# ========================
conn = sqlite3.connect(DB)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT,
    source TEXT,
    code TEXT,
    torrent_url TEXT,
    size REAL,
    seeds INTEGER,
    date_ts REAL
)
""")

conn.commit()

# ========================
# HELPERS
# ========================
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
    text=text.upper()
    m=re.search(r'([A-Z0-9]+-\d+)', text)
    if m:
        return m.group(1)
    m=re.search(r'PPV\s*(\d+)', text)
    if m:
        return f"PPV-{m.group(1)}"
    return None

# ========================
# IJAV
# ========================
def crawl_ijav(actor,url):
    print("\n🔵 IJAV:",actor)

    r=requests.get(url,headers=HEADERS,timeout=20)
    soup=BeautifulSoup(r.text,'html.parser')

    movie_links=[]
    for a in soup.select('div.name a'):
        movie_links.append(urljoin(url,a['href']))

    print("Movies:",len(movie_links))

    for m in movie_links:
        time.sleep(0.5)
        rm=requests.get(m,headers=HEADERS,timeout=20)
        msoup=BeautifulSoup(rm.text,'html.parser')

        code=extract_code(rm.text)
        if not code:
            continue

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

            c.execute("""
                INSERT INTO downloads(actor,source,code,torrent_url,size,seeds,date_ts)
                VALUES(?,?,?,?,?,?,?)
            """,(actor,"ijav",code,best[3],best[0],best[1],best[2]))

            conn.commit()

# ========================
# ONEJAV
# ========================
def crawl_onejav(actor,url):
    print("\n🟢 ONEJAV:",actor)

    r=requests.get(url,headers=HEADERS,timeout=20)
    soup=BeautifulSoup(r.text,'html.parser')

    links=[]
    for a in soup.find_all("a",href=True):
        if "/download/" in a['href']:
            links.append(urljoin(url,a['href']))

    print("Torrent links:",len(links))

    for l in links:
        code=extract_code(l)
        if not code:
            continue

        print("✔",code)

        c.execute("""
            INSERT INTO downloads(actor,source,code,torrent_url,size,seeds,date_ts)
            VALUES(?,?,?,?,?,?,?)
        """,(actor,"onejav",code,l,0,0,0))

        conn.commit()

# ========================
# RUN TEST
# ========================
actors = [
    ('Yuuka Minase','https://ijavtorrent.com/actress/yuuka-minase-2310/'),
    ('Rei Kamiki','https://ijavtorrent.com/actress/rei-kamiki-23668/'),
    ('Remu Suzumori','https://onejav.com/actress/Remu%20Suzumori')
]

for name,url in actors:
    if "ijavtorrent" in url:
        crawl_ijav(name,url)
    else:
        crawl_onejav(name,url)

print("\nDONE.")

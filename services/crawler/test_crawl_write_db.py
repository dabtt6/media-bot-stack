import requests, re, sqlite3, time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

HEADERS = {"User-Agent":"Mozilla/5.0"}
DB_PATH = "/app/data/crawler_test.db"

actors = [
    ('Yuuka Minase','https://ijavtorrent.com/actress/yuuka-minase-2310/'),
    ('Rei Kamiki','https://ijavtorrent.com/actress/rei-kamiki-23668/'),
    ('Remu Suzumori','https://onejav.com/actress/Remu%20Suzumori')
]

# =============================
# DB INIT
# =============================

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT,
            code TEXT,
            source TEXT,
            torrent_url TEXT,
            size REAL,
            seeds INTEGER,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

# =============================
# UTIL
# =============================

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

def save_db(actor, code, source, url, size=0, seeds=0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO downloads(actor,code,source,torrent_url,size,seeds,created_at)
        VALUES(?,?,?,?,?,?,?)
    """,(actor,code,source,url,size,seeds,datetime.now().isoformat()))
    conn.commit()
    conn.close()

# =============================
# IJAV LOGIC (GIỮ NGUYÊN)
# =============================

def crawl_ijav(actor,url):
    print("\n🔵 IJAV:",actor)

    r=requests.get(url,headers=HEADERS,timeout=20)
    soup=BeautifulSoup(r.text,'html.parser')

    movie_links=[urljoin(url,a['href']) for a in soup.select('div.name a')]
    print("Movies:",len(movie_links))

    all_best={}

    for m in movie_links:
        time.sleep(0.7)
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

        if torrents and code:
            torrents.sort(key=lambda x:(x[1],x[0],x[2]),reverse=True)
            best=torrents[0]

            if code not in all_best or (best[1],best[0]) > (all_best[code][1],all_best[code][0]):
                all_best[code]=best

    for code,best in all_best.items():
        print("✔",code,"|",round(best[0],1),"MB | Seeds:",best[1])
        save_db(actor,code,"ijav",best[3],best[0],best[1])

# =============================
# ONEJAV LOGIC (GIỮ CŨ)
# =============================

def crawl_onejav(actor,url):
    print("\n🟢 ONEJAV:",actor)

    r=requests.get(url,headers=HEADERS,timeout=20)
    soup=BeautifulSoup(r.text,'html.parser')

    count=0

    for a in soup.find_all("a",href=True):
        if "/torrent/" in a["href"] and "/download/" in a["href"]:
            full=urljoin(url,a["href"])

            code_match=re.search(r'/torrent/([a-z0-9]+)/',a["href"])
            if code_match:
                raw=code_match.group(1).upper()
                code=re.sub(r'(\D+)(\d+)',r'\1-\2',raw)

                print("✔",code)
                save_db(actor,code,"onejav",full)
                count+=1

    print("Torrent links:",count)

# =============================
# MAIN
# =============================

init_db()

for name,url in actors:
    if "ijavtorrent" in url:
        crawl_ijav(name,url)
    elif "onejav" in url:
        crawl_onejav(name,url)

print("\nDONE.")

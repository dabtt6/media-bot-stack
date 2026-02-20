import sqlite3, requests, re, time, random, threading
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DB = '/docker/media-stack/data/crawler/crawler_master_full.db'

# =========================
# SAFE SESSION
# =========================
def create_session():
    s = requests.Session()
    retries = Retry(total=5, backoff_factor=1,
                    status_forcelist=[429,500,502,503,504])
    adapter = HTTPAdapter(max_retries=retries,
                          pool_connections=20,
                          pool_maxsize=20)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({"User-Agent":"Mozilla/5.0"})
    return s

session = create_session()

# =========================
# INIT DB (main thread only)
# =========================
conn = sqlite3.connect(DB)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS actors(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
source TEXT,
url TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS crawl(
id INTEGER PRIMARY KEY AUTOINCREMENT,
actor_name TEXT,
source TEXT,
code TEXT,
torrent_url TEXT,
size_mb REAL,
seeds INTEGER,
date_ts REAL
)''')

c.execute('''CREATE TABLE IF NOT EXISTS queuedqbit(
id INTEGER PRIMARY KEY AUTOINCREMENT,
actor_name TEXT,
code TEXT UNIQUE,
chosen_source TEXT,
torrent_url TEXT,
size_mb REAL,
seeds INTEGER,
date_ts REAL,
status TEXT DEFAULT 'queued'
)''')

conn.commit()
conn.close()

# =========================
# TEST ACTORS
# =========================
actors = [
('Yuuka Minase','ijav','https://ijavtorrent.com/actress/yuuka-minase-2310/'),
('Rei Kamiki','ijav','https://ijavtorrent.com/actress/rei-kamiki-23668/'),
('Remu Suzumori','onejav','https://onejav.com/actress/Remu%20Suzumori')
]

# =========================
# UTILS
# =========================
def parse_size(text):
    text=text.lower().replace(' ','')
    if 'gb' in text:
        return float(text.replace('gb',''))*1024
    if 'mb' in text:
        return float(text.replace('mb',''))
    return 0

def parse_date(text):
    try:
        return datetime.strptime(text.strip(),'%d/%m/%Y').timestamp()
    except:
        return 0

def extract_code(text):
    m=re.search(r'([A-Z0-9]+-\d+)', text.upper())
    if m: return m.group(1)
    m=re.search(r'PPV\s*(\d+)', text.upper())
    if m: return f"PPV-{m.group(1)}"
    return None

# =========================
# CRAWL IJAV
# =========================
def crawl_ijav(actor,url):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    print(f"\n🔵 IJAV: {actor}")
    r=session.get(url,timeout=20)
    soup=BeautifulSoup(r.text,'html.parser')

    movies=[urljoin(url,a['href']) for a in soup.select('div.name a')]

    for m in movies:
        try:
            time.sleep(random.uniform(0.3,0.8))
            rm=session.get(m,timeout=20)
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
                torrents.sort(key=lambda x:(x[2],x[0],x[1]),reverse=True)
                best=torrents[0]

                c.execute('''
                INSERT INTO crawl(actor_name,source,code,torrent_url,size_mb,seeds,date_ts)
                VALUES(?,?,?,?,?,?,?)
                ''',(actor,'ijav',code,best[3],best[0],best[1],best[2]))
                conn.commit()

                print("✔",code,"|",round(best[0],1),"MB | Seeds:",best[1])

        except Exception as e:
            print("Error:",e)

    conn.close()

# =========================
# CRAWL ONEJAV
# =========================
def crawl_onejav(actor,url):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    print(f"\n🟢 ONEJAV: {actor}")
    r=session.get(url,timeout=20)
    soup=BeautifulSoup(r.text,'html.parser')

    links=[urljoin(url,a['href']) for a in soup.find_all('a',href=True)
           if '/torrent/' in a['href'] and '/download/' in a['href']]

    for l in links:
        code=extract_code(l.replace('/','-'))
        if code:
            c.execute('''
            INSERT INTO crawl(actor_name,source,code,torrent_url,size_mb,seeds,date_ts)
            VALUES(?,?,?,?,?,?,?)
            ''',(actor,'onejav',code,l,0,0,0))
            conn.commit()
            print("✔",code)

    conn.close()

# =========================
# BUILD QUEUE
# =========================
def build_queue():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    print("\n🟡 BUILD QUEUE")

    codes=c.execute("SELECT DISTINCT code FROM crawl").fetchall()
    for (code,) in codes:
        rows=c.execute("SELECT actor_name,source,torrent_url,size_mb,seeds,date_ts FROM crawl WHERE code=?",(code,)).fetchall()

        ijav=[r for r in rows if r[1]=='ijav']
        one=[r for r in rows if r[1]=='onejav']

        chosen=None
        if ijav:
            chosen=sorted(ijav,key=lambda x:(x[5],x[3],x[4]),reverse=True)[0]
        elif one:
            chosen=one[0]

        if chosen:
            c.execute('''
            INSERT OR IGNORE INTO queuedqbit(actor_name,code,chosen_source,torrent_url,size_mb,seeds,date_ts,status)
            VALUES(?,?,?,?,?,?,?,'queued')
            ''',(chosen[0],code,chosen[1],chosen[2],chosen[3],chosen[4],chosen[5]))
            conn.commit()

    total=c.execute("SELECT COUNT(*) FROM queuedqbit").fetchone()[0]
    print("Total queued:",total)

    conn.close()

# =========================
# RUN
# =========================
threads=[]
for name,source,url in actors:
    if source=='ijav':
        t=threading.Thread(target=crawl_ijav,args=(name,url))
    else:
        t=threading.Thread(target=crawl_onejav,args=(name,url))
    t.start()
    threads.append(t)

for t in threads:
    t.join()

build_queue()

print("\n🎯 DONE")

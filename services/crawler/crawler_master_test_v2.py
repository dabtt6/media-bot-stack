import sqlite3, requests, re, time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

DB = "crawler_master_test_v2.db"
HEADERS = {"User-Agent":"Mozilla/5.0"}

# ======================
# INIT DB
# ======================
conn = sqlite3.connect(DB)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS actors(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
source TEXT,
url TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS crawl(
id INTEGER PRIMARY KEY AUTOINCREMENT,
actor_name TEXT,
source TEXT,
code TEXT,
torrent_url TEXT,
size_mb REAL,
seeds INTEGER,
date_ts REAL
)""")

c.execute("""CREATE TABLE IF NOT EXISTS queuedqbit(
id INTEGER PRIMARY KEY AUTOINCREMENT,
actor_name TEXT,
code TEXT UNIQUE,
chosen_source TEXT,
torrent_url TEXT,
size_mb REAL,
seeds INTEGER,
date_ts REAL
)""")

conn.commit()

# ======================
# TEST ACTORS
# ======================
actors = [
("Yuuka Minase","ijav","https://ijavtorrent.com/actress/yuuka-minase-2310/"),
("Rei Kamiki","ijav","https://ijavtorrent.com/actress/rei-kamiki-23668/"),
("Remu Suzumori","onejav","https://onejav.com/actress/Remu%20Suzumori")
]

# ======================
# UTILS
# ======================
def parse_size(text):
    text=text.lower().replace(" ","")
    if "gb" in text:
        return float(text.replace("gb",""))*1024
    if "mb" in text:
        return float(text.replace("mb",""))
    return 0

def parse_date(text):
    try:
        return datetime.strptime(text,"%d/%m/%Y").timestamp()
    except:
        return 0

def extract_code(text):
    text=text.upper()
    m=re.search(r'([A-Z]{2,10}-\d{2,6})',text)
    if m: return m.group(1)
    m=re.search(r'PPV\s?(\d{5,7})',text)
    if m: return "PPV-"+m.group(1)
    return None

def save_crawl(actor,source,code,url,size,seeds,date):
    c.execute("""
    INSERT INTO crawl(actor_name,source,code,torrent_url,size_mb,seeds,date_ts)
    VALUES(?,?,?,?,?,?,?)
    """,(actor,source,code,url,size,seeds,date))
    conn.commit()

# ======================
# IJAV CRAWL
# ======================
def crawl_ijav(name,url):
    print("\n🔵 IJAV:",name)
    r=requests.get(url,headers=HEADERS,timeout=20)
    soup=BeautifulSoup(r.text,"html.parser")

    movie_links=[urljoin(url,a['href']) for a in soup.select("div.name a")]
    print("Movies:",len(movie_links))

    for m in movie_links[:10]:
        time.sleep(0.5)
        rm=requests.get(m,headers=HEADERS,timeout=20)
        msoup=BeautifulSoup(rm.text,"html.parser")

        code=extract_code(m)
        rows=msoup.find_all("tr")

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
                for a in tr.find_all("a",href=True):
                    if "/download/" in a['href']:
                        dl=urljoin(url,a['href'])
                        break

                if size>0 and dl:
                    torrents.append((size,seeds,date,dl))

        if torrents:
            torrents.sort(key=lambda x:(x[2],x[0],x[1]),reverse=True)
            best=torrents[0]
            print("✔",code,"|",round(best[0],1),"MB | Seeds:",best[1])
            save_crawl(name,"ijav",code,best[3],best[0],best[1],best[2])

# ======================
# ONEJAV CRAWL
# ======================
def crawl_onejav(name,url):
    print("\n🟢 ONEJAV:",name)
    r=requests.get(url,headers=HEADERS,timeout=20)
    soup=BeautifulSoup(r.text,"html.parser")

    links=[a['href'] for a in soup.find_all("a",href=True) if "/download/" in a['href']]
    print("Torrent links:",len(links))

    for l in links:
        full="https://onejav.com"+l
        code=extract_code(l)
        if code:
            print("✔",code)
            save_crawl(name,"onejav",code,full,0,0,0)

# ======================
# BUILD QUEUE
# ======================
def build_queue():
    print("\n🟡 BUILD QUEUE")
    rows=c.execute("""
    SELECT actor_name, code
    FROM crawl
    GROUP BY actor_name, code
    """).fetchall()

    for actor_name,code in rows:
        ijav=c.execute("""
        SELECT torrent_url,size_mb,seeds,date_ts
        FROM crawl
        WHERE code=? AND source='ijav'
        ORDER BY date_ts DESC,size_mb DESC,seeds DESC
        LIMIT 1
        """,(code,)).fetchone()

        if ijav:
            chosen=("ijav",)+ijav
        else:
            one=c.execute("""
            SELECT torrent_url,size_mb,seeds,date_ts
            FROM crawl
            WHERE code=? AND source='onejav'
            LIMIT 1
            """,(code,)).fetchone()
            if not one:
                continue
            chosen=("onejav",)+one

        c.execute("""
        INSERT OR IGNORE INTO queuedqbit
        (actor_name,code,chosen_source,torrent_url,size_mb,seeds,date_ts)
        VALUES(?,?,?,?,?,?,?)
        """,(actor_name,code)+chosen)
        conn.commit()

    print("Queued total:",
          c.execute("SELECT COUNT(*) FROM queuedqbit").fetchone()[0])

# ======================
# MAIN
# ======================
for name,source,url in actors:
    if source=="ijav":
        crawl_ijav(name,url)
    else:
        crawl_onejav(name,url)

build_queue()

print("\nDONE.")

import sqlite3, requests, re, time, threading
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

DB = '/docker/media-stack/data/crawler/crawler_master_test.db'
HEADERS = {'User-Agent':'Mozilla/5.0'}

# =========================
# INIT DB
# =========================
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS crawl(
id INTEGER PRIMARY KEY AUTOINCREMENT,
actor_name TEXT,
source TEXT,
code TEXT,
torrent_url TEXT,
size_mb REAL,
seeds INTEGER,
date_ts REAL
)
''')
conn.commit()

lock = threading.Lock()

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
        return datetime.strptime(text.strip(), '%d/%m/%Y').timestamp()
    except:
        return 0

def extract_ijav_code(text):
    m=re.search(r'([A-Z0-9]+-\d+)', text.upper())
    return m.group(1) if m else None

def extract_onejav_code(url):
    m = re.search(r'/torrent/([^/]+)/download/', url)
    if m:
        raw = m.group(1).upper()
        m2 = re.match(r'([A-Z]+)(\d+)', raw)
        if m2:
            return f"{m2.group(1)}-{m2.group(2)}"
    return None

def save_db(actor,source,code,url,size,seeds,date):
    if not code:
        return
    with lock:
        c.execute('''
        INSERT OR IGNORE INTO crawl(actor_name,source,code,torrent_url,size_mb,seeds,date_ts)
        VALUES(?,?,?,?,?,?,?)
        ''',(actor,source,code,url,size,seeds,date))
        conn.commit()

# =========================
# IJAV
# =========================
def crawl_ijav(actor,url):
    print(f"\n🔵 IJAV: {actor}")
    try:
        r=requests.get(url,headers=HEADERS,timeout=20)
        soup=BeautifulSoup(r.text,'html.parser')
        movies=[urljoin(url,a['href']) for a in soup.select('div.name a')]

        for m in movies:
            time.sleep(0.5)
            try:
                rm=requests.get(m,headers=HEADERS,timeout=20)
                msoup=BeautifulSoup(rm.text,'html.parser')

                code=extract_ijav_code(m)
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
                    save_db(actor,"ijav",code,best[3],best[0],best[1],best[2])

            except Exception as e:
                print("Error movie:",e)

    except Exception as e:
        print("Error actor:",e)

# =========================
# ONEJAV
# =========================
def crawl_onejav(actor,url):
    print(f"\n🟢 ONEJAV: {actor}")
    try:
        r=requests.get(url,headers=HEADERS,timeout=20)
        soup=BeautifulSoup(r.text,'html.parser')

        links=[]
        for a in soup.find_all('a',href=True):
            if '/torrent/' in a['href'] and '/download/' in a['href']:
                links.append(urljoin(url,a['href']))

        for link in links:
            code=extract_onejav_code(link)
            print("✔",code)
            save_db(actor,"onejav",code,link,0,0,0)

    except Exception as e:
        print("Error actor:",e)

# =========================
# TEST ACTORS
# =========================
actors = [
('Yuuka Minase','ijav','https://ijavtorrent.com/actress/yuuka-minase-2310/'),
('Rei Kamiki','ijav','https://ijavtorrent.com/actress/rei-kamiki-23668/'),
('Remu Suzumori','onejav','https://onejav.com/actress/Remu%20Suzumori')
]

threads=[]
for name,source,url in actors:
    if source=="ijav":
        t=threading.Thread(target=crawl_ijav,args=(name,url))
    else:
        t=threading.Thread(target=crawl_onejav,args=(name,url))
    t.start()
    threads.append(t)

for t in threads:
    t.join()

print("\nDONE.")

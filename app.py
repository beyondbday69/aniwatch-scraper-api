from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import HTMLResponse
import requests
from bs4 import BeautifulSoup
import re
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal

app = FastAPI(title="AniwatchTV Unofficial API")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
AJAX_HEADERS = {**HEADERS, "X-Requested-With": "XMLHttpRequest"}
BASE_URL = "https://aniwatchtv.to"

def get_slug(url):
    if not url: return ""
    return url.split('?')[0].strip('/').replace('watch/', '', 1)

def parse_card(el):
    # Support for standard cards and spotlight cards
    t = el.find(['h3', 'h2', 'div'], class_=['film-name', 'film-title', 'desi-head-title']) or el.find('a', title=True)
    a = el.find('a', class_='film-poster') or el.find('a', href=True)
    i = el.find('img')
    ts = el.find('div', class_='tick-sub')
    td = el.find('div', class_='tick-dub')
    te = el.find('div', class_='tick-eps')
    
    jname = ""
    dynamic_name = el.find(class_='dynamic-name')
    if dynamic_name and dynamic_name.get('data-jname'):
        jname = dynamic_name.get('data-jname')
        
    type_name = ""
    duration = ""
    release_date = ""
    for fdi in el.find_all(['span', 'div'], class_=['fdi-item', 'scd-item']):
        if fdi.find(class_=re.compile(r'tick')):
            continue
            
        text = fdi.get_text().strip()
        if not text or text in ["HD", "SD"]:
            continue
            
        if "m" in text or "h" in text:
            duration = text
        elif re.search(r'\d{4}', text): # Looks like a date (e.g. Oct 20, 1999)
            release_date = text
        elif not type_name:
            type_name = text
            
    desc_tag = el.find('div', class_='desi-description')
    description = desc_tag.get_text().strip() if desc_tag else ""
    
    return {
        "title": t.get('title') or t.get_text().strip() if t else "Unknown",
        "japanese_title": jname,
        "anime_id": get_slug(a['href']) if a else "",
        "image": i.get('data-src') or i.get('src') or "" if i else "",
        "type": type_name,
        "duration": duration,
        "release_date": release_date,
        "sub": ts.get_text().strip() if ts else None,
        "dub": td.get_text().strip() if td else None,
        "episodes": te.get_text().strip() if te else None,
        "description": description
    }

@app.get("/home")
def get_home():
    try:
        r = requests.get(f"{BASE_URL}/home", headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')
        data = {
            "spotlight": [],
            "trending": [], 
            "top_airing": [], 
            "most_popular": [], 
            "most_favorite": [], 
            "latest_completed": [], 
            "latest_episodes": [],
            "genres": []
        }
        
        # Spotlights (Hero Slider)
        for item in soup.select("#slider .swiper-slide"):
            data["spotlight"].append(parse_card(item))
            
        # Trending
        for item in soup.select("#trending-home .swiper-slide"):
            data["trending"].append(parse_card(item))
            
        # Sidebar Blocks (Top Airing, etc.)
        for h in soup.select(".anif-block-header"):
            k = h.get_text().strip().lower().replace(" ", "_")
            if k in data:
                ul = h.find_next_sibling("div", class_="anif-block-ul")
                if ul:
                    for li in ul.find_all("li"):
                        data[k].append(parse_card(li))
                        
        # Latest Episodes
        for item in soup.find_all('div', class_=re.compile(r'flw-item')):
            data["latest_episodes"].append(parse_card(item))
            
        # Genres from navigation menu
        genres_set = set()
        for a in soup.find_all("a", href=True):
            if "/genre/" in a["href"]:
                genres_set.add(a.text.strip())
        data["genres"] = sorted(list(genres_set))
            
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/popular")
def get_popular():
    r = requests.get(f"{BASE_URL}/home", headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    return {"results": [parse_card(i) for i in soup.find_all('div', class_=re.compile(r'flw-item'))]}

@app.get("/search")
def search(q: str = Query(...)):
    r = requests.get(f"{BASE_URL}/search?keyword={q}", headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    return {"results": [parse_card(i) for i in soup.find_all('div', class_=re.compile(r'flw-item'))]}

@app.get("/anime/{anime_id}")
def get_anime(anime_id: str):
    if anime_id.isdigit():
        s = BeautifulSoup(requests.get(f"{BASE_URL}/search?keyword={anime_id}", headers=HEADERS).text, 'html.parser')
        p = re.compile(rf"-{anime_id}$")
        for a in s.find_all('a', href=True):
            h = a['href'].split('?')[0]
            if p.search(h): anime_id = h.lstrip('/'); break
    r = requests.get(f"{BASE_URL}/{anime_id}", headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    details = {}
    info = soup.find('div', class_='anisc-info')
    if info:
        for item in info.find_all('div', class_='item'):
            text = item.get_text().strip()
            if ':' in text:
                k, v = text.split(':', 1)
                details[k.strip().lower()] = v.strip()
    return {
        "anime_id": anime_id,
        "title": soup.find('h2', class_='film-name').get_text().strip() if soup.find('h2', class_='film-name') else "Unknown",
        "description": soup.find('div', class_='film-description').get_text().strip() if soup.find('div', class_='film-description') else "",
        "image": soup.find('img', class_='film-poster-img').get('src') if soup.find('img', class_='film-poster-img') else "",
        "details": details,
        "seasons": [{"title": a.find('div', class_='title').get_text().strip(), "anime_id": get_slug(a.get('href'))} for a in soup.select(".os-list a")] if soup.select(".os-list a") else []
    }

@app.get("/episodes/{anime_id}")
def get_episodes(anime_id: str):
    if not anime_id.isdigit():
        m = re.search(r'-(\d+)$', anime_id)
        if m: anime_id = m.group(1)
    r = requests.get(f"{BASE_URL}/ajax/v2/episode/list/{anime_id}", headers=AJAX_HEADERS)
    s = BeautifulSoup(r.json()["html"], 'html.parser')
    return {"episodes": [{"ep_id": a["data-id"], "number": a["data-number"], "title": a["title"]} for a in s.find_all("a", class_="ep-item")]}

@app.get("/servers/{ep_id}")
def get_servers(ep_id: str):
    r = requests.get(f"{BASE_URL}/ajax/v2/episode/servers?episodeId={ep_id}", headers=AJAX_HEADERS)
    s = BeautifulSoup(r.json()["html"], 'html.parser')
    return {"servers": [{"server_id": d["data-id"], "name": d.get_text().strip(), "type": d["data-type"]} for d in s.find_all("div", class_="server-item")]}

@app.get("/megaplay/{ep_id}")
def get_megaplay(ep_id: str):
    return {
        "episode_id": ep_id,
        "sub": f"https://megaplay.buzz/stream/s-2/{ep_id}/sub",
        "dub": f"https://megaplay.buzz/stream/s-2/{ep_id}/dub",
        "raw": f"https://megaplay.buzz/stream/s-2/{ep_id}/raw"
    }

@app.get("/sources/{server_id}")
def get_sources(server_id: str):
    return requests.get(f"{BASE_URL}/ajax/v2/episode/sources?id={server_id}", headers=AJAX_HEADERS).json()

@app.get("/tester", response_class=HTMLResponse)
def tester():
    return HTMLResponse("<html><body style='background:#111;color:#eee'><input id=u style='width:80%'><button onclick='f.src=u.value'>Go</button><iframe id=f style='width:100%;height:90%;border:none' allowfullscreen></iframe></body></html>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6969)

from fastapi import FastAPI, HTTPException, Query, Path, Request
from fastapi.responses import HTMLResponse
import requests
from bs4 import BeautifulSoup
import re
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal
import json

app = FastAPI(title="AniwatchTV Unofficial API & Website")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
AJAX_HEADERS = {**HEADERS, "X-Requested-With": "XMLHttpRequest"}
BASE_URL = "https://aniwatchtv.to"

# --- UTILS ---

def get_slug(url):
    if not url: return ""
    return url.split('?')[0].strip('/').replace('watch/', '', 1)

def parse_card(el):
    t_el = el.find(['h3', 'h2', 'div'], class_=['film-name', 'film-title', 'desi-head-title']) or el.find('a', title=True)
    a_el = el.find('a', class_=['film-poster', 'film-poster-ahref']) or el.find('a', href=True)
    i_el = el.find('img')
    ts = el.find('div', class_='tick-sub')
    td = el.find('div', class_='tick-dub')
    te = el.find('div', class_='tick-eps')
    
    title = t_el.get('title') or t_el.get_text().strip() if t_el else "Unknown"
    anime_id = get_slug(a_el['href']) if a_el else ""
    image = i_el.get('data-src') or i_el.get('src') or "" if i_el else ""
    
    jname = ""
    dynamic_name = el.find(class_='dynamic-name')
    if dynamic_name and dynamic_name.get('data-jname'): jname = dynamic_name.get('data-jname')
    
    type_name = ""
    duration = ""
    for fdi in el.find_all(['span', 'div'], class_=['fdi-item', 'scd-item']):
        if fdi.find(class_=re.compile(r'tick')): continue
        text = fdi.get_text().strip()
        if not text or text in ["HD", "SD"]: continue
        if "m" in text or "h" in text: duration = text
        elif re.search(r'\d{4}', text): pass
        elif not type_name: type_name = text
            
    return {
        "title": title,
        "japanese_title": jname,
        "anime_id": anime_id,
        "image": image,
        "type": type_name,
        "duration": duration,
        "sub": ts.get_text().strip() if ts else None,
        "dub": td.get_text().strip() if td else None,
        "episodes": te.get_text().strip() if te else None,
        "description": el.find('div', class_='desi-description').get_text().strip() if el.find('div', class_='desi-description') else ""
    }

# --- API ---

@app.get("/home")
def get_home_api():
    r = requests.get(f"{BASE_URL}/home", headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    data = {"spotlight":[], "trending":[], "top_airing":[], "most_popular":[], "most_favorite":[], "latest_completed":[], "latest_episodes":[], "genres":[]}
    for i in soup.select("#slider .swiper-slide"): data["spotlight"].append(parse_card(i))
    for i in soup.select("#trending-home .swiper-slide"): data["trending"].append(parse_card(i))
    for h in soup.select(".anif-block-header"):
        k = h.get_text().strip().lower().replace(" ", "_")
        if k in data:
            ul = h.find_next_sibling("div", class_="anif-block-ul")
            if ul:
                for li in ul.find_all("li"): data[k].append(parse_card(li))
    for i in soup.find_all('div', class_=re.compile(r'flw-item')): data["latest_episodes"].append(parse_card(i))
    g_set = set()
    for a in soup.find_all("a", href=True):
        if "/genre/" in a["href"]: g_set.add(a.text.strip())
    data["genres"] = sorted(list(g_set))
    return data

@app.get("/genre/{name}")
def get_genre_api(name: str, page: int = 1):
    r = requests.get(f"{BASE_URL}/genre/{name}?page={page}", headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    return {"results": [parse_card(i) for i in soup.find_all('div', class_=re.compile(r'flw-item'))]}

@app.get("/search")
def search_api(q: str = Query(...)):
    r = requests.get(f"{BASE_URL}/search?keyword={q}", headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    return {"results": [parse_card(i) for i in soup.find_all('div', class_=re.compile(r'flw-item'))]}

@app.get("/anime/{aid}")
def get_anime_api(aid: str):
    if aid.isdigit():
        s = BeautifulSoup(requests.get(f"{BASE_URL}/search?keyword={aid}", headers=HEADERS).text, 'html.parser')
        p = re.compile(rf"-{aid}$")
        for a in s.find_all('a', href=True):
            h = a['href'].split('?')[0]
            if p.search(h): aid = h.lstrip('/'); break
    r = requests.get(f"{BASE_URL}/{aid}", headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    details = {}
    info = soup.find('div', class_='anisc-info')
    if info:
        for it in info.find_all('div', class_='item'):
            txt = it.get_text().strip()
            if ':' in txt: k, v = txt.split(':', 1); details[k.strip().lower()] = v.strip()
    return {
        "anime_id": aid,
        "title": soup.find('h2', class_='film-name').get_text().strip() if soup.find('h2', class_='film-name') else "Unknown",
        "description": soup.find('div', class_='film-description').get_text().strip() if soup.find('div', class_='film-description') else "",
        "image": soup.find('img', class_='film-poster-img').get('src') if soup.find('img', class_='film-poster-img') else "",
        "details": details,
        "seasons": [{"title": a.find('div', class_='title').text.strip(), "anime_id": get_slug(a['href'])} for a in soup.select(".os-list a")]
    }

@app.get("/episodes/{aid}")
def get_episodes_api(aid: str):
    if not aid.isdigit():
        m = re.search(r'-(\d+)$', aid)
        if m: aid = m.group(1)
    r = requests.get(f"{BASE_URL}/ajax/v2/episode/list/{aid}", headers=AJAX_HEADERS)
    s = BeautifulSoup(r.json()["html"], 'html.parser')
    return {"episodes": [{"ep_id": a["data-id"], "number": a["data-number"], "title": a["title"]} for a in s.find_all("a", class_="ep-item")]}

@app.get("/megaplay/{eid}")
def get_megaplay_api(eid: str):
    return {"sub": f"https://megaplay.buzz/stream/s-2/{eid}/sub", "dub": f"https://megaplay.buzz/stream/s-2/{eid}/dub"}

# --- UI ---

STYLE = """
<style>
:root { --bg: #0b0b0b; --sidebar: #141414; --primary: #ffdd95; --text: #eee; --muted: #999; }
body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; }
header { background: rgba(20,20,20,0.9); backdrop-filter: blur(10px); padding: 15px 5%; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #333; position: sticky; top:0; z-index:1000; }
.logo { color: var(--primary); font-size: 24px; font-weight: bold; text-decoration: none; }
.search-bar { background: #222; border-radius: 20px; padding: 5px 15px; display: flex; }
.search-bar input { background: transparent; border: none; color: white; outline: none; width: 200px; }
.hero { height: 60vh; position: relative; display: flex; align-items: flex-end; padding: 40px 5%; background: #000; overflow: hidden; margin-bottom: 30px; }
.hero-img { position: absolute; top:0; left:0; width:100%; height:100%; object-fit: cover; opacity: 0.4; }
.hero-content { position: relative; z-index: 10; max-width: 700px; }
.btn-p { background: var(--primary); color: black; padding: 12px 25px; border-radius: 5px; text-decoration: none; font-weight: bold; display: inline-block; margin-top: 15px; }
.container { padding: 0 5%; display: grid; grid-template-columns: 1fr 300px; gap: 40px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 15px; }
.card { background: #1a1a1a; border-radius: 5px; overflow: hidden; text-decoration: none; color: inherit; border: 1px solid #222; }
.card img { width: 100%; aspect-ratio: 2/3; object-fit: cover; }
.card-info { padding: 10px; font-size: 13px; }
.sidebar-box { background: var(--sidebar); padding: 20px; border-radius: 8px; margin-bottom: 30px; }
.t-row { display: flex; gap: 10px; margin-bottom: 15px; text-decoration: none; color: inherit; font-size: 13px; }
.t-row img { width: 45px; aspect-ratio: 2/3; object-fit: cover; }
.badge { background: var(--primary); color: #000; font-size: 10px; padding: 2px 4px; border-radius: 2px; font-weight: bold; margin-right: 5px; }
.ep-link { background: #222; color: #fff; text-decoration: none; padding: 8px; border-radius: 3px; text-align: center; font-size: 12px; border: 1px solid #333; }
.ep-link.active { background: var(--primary); color: #000; }
.player-wrap { aspect-ratio: 16/9; background: #000; border-radius: 8px; overflow: hidden; margin-bottom: 20px; }
@media (max-width: 900px) { .container { display: block; } .sidebar { margin-top: 40px; } }
</style>
"""

@app.get("/explore", response_class=HTMLResponse)
def explore_ui():
    d = get_home_api()
    h = d["spotlight"][0] if d["spotlight"] else None
    hero = f'<div class="hero"><img src="{h["image"]}" class="hero-img"><div class="hero-content"><h1>{h["title"]}</h1><p style="color:#ccc">{h["description"][:200]}...</p><a href="/watch-page?id={h["anime_id"]}" class="btn-p">Watch Now</a></div></div>' if h else ""
    latest = "".join([f'<a href="/anime-page?id={a["anime_id"]}" class="card"><img src="{a["image"]}"><div class="card-info"><b>{a["title"]}</b></div></a>' for a in d["latest_episodes"]])
    trending = "".join([f'<a href="/anime-page?id={a["anime_id"]}" class="t-row"><b>{str(i+1).zfill(2)}</b><img src="{a["image"]}"><div>{a["title"]}</div></a>' for i,a in enumerate(d["trending"][:10])])
    genres = "".join([f'<a href="/genre-page?name={g.lower()}" style="font-size:12px; color:#aaa; margin:5px; text-decoration:none;">{g}</a>' for g in d["genres"]])
    return f"<html><head>{STYLE}</head><body><header><a href='/explore' class='logo'>AniwatchTV</a><div class='search-bar'><form action='/q'><input name='q' placeholder='Search...'></form></div></header>{hero}<div class='container'><div><h2>Latest</h2><div class='grid'>{latest}</div></div><div class='sidebar'><div class='sidebar-box'><h3>Trending</h3>{trending}</div><div class='sidebar-box'><h3>Genres</h3><div style='display:flex;flex-wrap:wrap'>{genres}</div></div></div></div></body></html>"

@app.get("/anime-page", response_class=HTMLResponse)
def anime_ui(id: str):
    a = get_anime_api(id)
    e = get_episodes_api(id)
    eps = "".join([f'<a href="/watch-page?id={id}&ep={i["ep_id"]}" class="ep-link">{i["number"]}</a>' for i in e["episodes"]])
    seasons = "".join([f'<a href="/anime-page?id={s["anime_id"]}" style="color:{"#ffdd95" if s["anime_id"]==id else "#fff"}; margin-right:10px; text-decoration:none;">{s["title"]}</a>' for s in a["seasons"]])
    return f"<html><head>{STYLE}</head><body><header><a href='/explore' class='logo'>AniwatchTV</a></header><div class='container' style='display:block; max-width:1000px; margin:auto;'><div style='display:flex; gap:30px; margin-top:40px;'><img src='{a["image"]}' style='width:250px; border-radius:8px;'><div><h1>{a["title"]}</h1><p>{a["description"]}</p><div style='margin-bottom:20px'>{seasons}</div><h3>Episodes</h3><div style='display:grid; grid-template-columns:repeat(auto-fill, minmax(50px,1fr)); gap:10px;'>{eps}</div></div></div></div></body></html>"

@app.get("/watch-page", response_class=HTMLResponse)
def watch_ui(id: str, ep: str = None, type: str = "sub"):
    a = get_anime_api(id)
    e = get_episodes_api(id)
    curr = ep or (e["episodes"][0]["ep_id"] if e["episodes"] else None)
    nxt = ""
    for i, x in enumerate(e["episodes"]):
        if x["ep_id"] == curr and i+1 < len(e["episodes"]): nxt = f"/watch-page?id={id}&ep={e['episodes'][i+1]['ep_id']}&type={type}"
    eps = "".join([f"<a href='/watch-page?id={id}&ep={x['ep_id']}&type={type}' class='ep-link {'active' if x['ep_id']==curr else ''}'>{x['number']}</a>" for x in e['episodes']])
    src = f"https://megaplay.buzz/stream/s-2/{curr}/{type}"
    return f"<html><head>{STYLE}</head><body><header><a href='/explore' class='logo'>AniwatchTV</a></header><div class='container' style='display:block; max-width:1100px; margin:auto; margin-top:30px;'><div class='player-wrap'><iframe src='{src}' style='width:100%;height:100%;border:none' allowfullscreen sandbox='allow-scripts allow-same-origin allow-forms'></iframe></div><div style='display:flex; justify-content:space-between; align-items:center; background:#181818; padding:15px; border-radius:8px;'><div>Type: <a href='/watch-page?id={id}&ep={curr}&type=sub' style='color:{'#ffdd95' if type=='sub' else '#fff'}'>SUB</a> | <a href='/watch-page?id={id}&ep={curr}&type=dub' style='color:{'#ffdd95' if type=='dub' else '#fff'}'>DUB</a></div><div>AutoNext: <input type='checkbox' id='an' checked></div></div><h1>{a['title']}</h1><div style='background:#181818; padding:20px; border-radius:8px; margin-top:20px;'><h3>Episodes</h3><div style='display:grid; grid-template-columns:repeat(auto-fill, minmax(50px,1fr)); gap:10px;'>{eps}</div></div></div><script>window.addEventListener('message',e=>{{ let d=e.data; if(typeof d==='string'){{try{{d=JSON.parse(d)}}catch(ex){{}}}} if((d.event==='complete'||d.type==='complete')&&document.getElementById('an').checked&&'{nxt}')location.href='{nxt}'}})</script></body></html>"

@app.get("/q", response_class=HTMLResponse)
def search_ui_res(q: str):
    d = search_api(q)
    cards = "".join([f'<a href="/anime-page?id={a["anime_id"]}" class="card"><img src="{a["image"]}"><div class="card-info"><b>{a["title"]}</b></div></a>' for a in d["results"]])
    return f"<html><head>{STYLE}</head><body><header><a href='/explore' class='logo'>AniwatchTV</a></header><div class='container' style='display:block;'><h2>Search: {q}</h2><div class='grid'>{cards}</div></div></body></html>"

@app.get("/genre-page", response_class=HTMLResponse)
def genre_ui_res(name: str):
    d = get_genre_api(name)
    cards = "".join([f'<a href="/anime-page?id={a["anime_id"]}" class="card"><img src="{a["image"]}"><div class="card-info"><b>{a["title"]}</b></div></a>' for a in d["results"]])
    return f"<html><head>{STYLE}</head><body><header><a href='/explore' class='logo'>AniwatchTV</a></header><div class='container' style='display:block;'><h2>Genre: {name}</h2><div class='grid'>{cards}</div></div></body></html>"

@app.get("/", response_class=HTMLResponse)
def index():
    return f"<html><head>{STYLE}</head><body style='display:flex;align-items:center;justify-content:center;height:100vh;text-align:center'><div class='sidebar-box' style='max-width:600px'><h1>AniwatchTV Unofficial</h1><a href='/explore' class='btn-p'>Launch Website</a><div style='text-align:left; margin-top:30px; font-size:14px;'><h3>API Docs</h3><code>GET /home</code> - Spotlight, Trending, Genres<br><code>GET /search?q=</code> - Search anime<br><code>GET /anime/{{id}}</code> - Details & Seasons<br><code>GET /episodes/{{id}}</code> - Episode IDs<br><code>GET /megaplay/{{eid}}</code> - Video links</div></div></body></html>"

@app.get("/tester", response_class=HTMLResponse)
def tester_page():
    return HTMLResponse("<html><body style='background:#000;color:#fff;margin:0'><input id=u style='width:70%;padding:10px'><button onclick='f.src=u.value'>Go</button><iframe id=f style='width:100%;height:90vh;border:none' allowfullscreen sandbox='allow-scripts allow-same-origin allow-forms'></iframe></body></html>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6969)

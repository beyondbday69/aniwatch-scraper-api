from fastapi import FastAPI, HTTPException, Query, Path, Request
from fastapi.responses import HTMLResponse
import requests
from bs4 import BeautifulSoup
import re
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal

app = FastAPI(title="AniwatchTV Unofficial")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

HEADERS = {"User-Agent": "Mozilla/5.0"}
AJAX_HEADERS = {**HEADERS, "X-Requested-With": "XMLHttpRequest"}
BASE_URL = "https://aniwatchtv.to"

def get_slug(url):
    if not url: return ""
    return url.split('?')[0].strip('/').replace('watch/', '', 1)

def parse_card(el):
    t = el.find(['h3', 'h2', 'div'], class_=['film-name', 'film-title', 'desi-head-title']) or el.find('a', title=True)
    a = el.find('a', class_=['film-poster', 'film-poster-ahref']) or el.find('a', href=True)
    i = el.find('img')
    ts = el.find('div', class_='tick-sub'); td = el.find('div', class_='tick-dub'); te = el.find('div', class_='tick-eps')
    type_name = ""; duration = ""
    for fdi in el.find_all(['span', 'div'], class_=['fdi-item', 'scd-item']):
        if fdi.find(class_=re.compile(r'tick')): continue
        text = fdi.get_text().strip()
        if "m" in text or "h" in text: duration = text
        elif text and text not in ["HD", "SD"]: type_name = text
    return {
        "title": t.get('title') or t.get_text().strip() if t else "Unknown",
        "anime_id": get_slug(a['href']) if a else "",
        "image": i.get('data-src') or i.get('src') or "" if i else "",
        "type": type_name, "duration": duration,
        "sub": ts.get_text().strip() if ts else None, "dub": td.get_text().strip() if td else None
    }

@app.get("/home")
def get_home():
    r = requests.get(f"{BASE_URL}/home", headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    data = {"spotlight": [], "trending": [], "latest_episodes": []}
    for item in soup.select("#slider .swiper-slide"): data["spotlight"].append(parse_card(item))
    for item in soup.select("#trending-home .swiper-slide"): data["trending"].append(parse_card(item))
    for item in soup.find_all('div', class_=re.compile(r'flw-item')): data["latest_episodes"].append(parse_card(item))
    return data

@app.get("/search")
def search_api(q: str = Query(...)):
    r = requests.get(f"{BASE_URL}/search?keyword={q}", headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    return {"results": [parse_card(i) for i in soup.find_all('div', class_=re.compile(r'flw-item'))]}

@app.get("/anime/{anime_id}")
def get_anime(anime_id: str):
    r = requests.get(f"{BASE_URL}/{anime_id}", headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    details = {}; info = soup.find('div', class_='anisc-info')
    if info:
        for item in info.find_all('div', class_='item'):
            text = item.get_text().strip()
            if ':' in text: k, v = text.split(':', 1); details[k.strip().lower()] = v.strip()
    return {
        "title": soup.find('h2', class_='film-name').get_text().strip() if soup.find('h2', class_='film-name') else "Unknown",
        "description": soup.find('div', class_='film-description').get_text().strip() if soup.find('div', class_='film-description') else "",
        "image": soup.find('img', class_='film-poster-img').get('src') if soup.find('img', class_='film-poster-img') else "",
        "details": details, "seasons": [{"title": a.find('div', class_='title').get_text().strip(), "anime_id": get_slug(a.get('href'))} for a in soup.select(".os-list a")]
    }

@app.get("/episodes/{anime_id}")
def get_episodes(anime_id: str):
    if not anime_id.isdigit():
        m = re.search(r'-(\d+)$', anime_id)
        if m: anime_id = m.group(1)
    r = requests.get(f"{BASE_URL}/ajax/v2/episode/list/{anime_id}", headers=AJAX_HEADERS)
    s = BeautifulSoup(r.json()["html"], 'html.parser')
    return {"episodes": [{"ep_id": a["data-id"], "number": a["data-number"], "title": a["title"]} for a in s.find_all("a", class_="ep-item")]}

SHARED_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0">
<style>
    :root { 
        --bg: #050505; --card: #121218; --primary: #ffdd95; --accent: #ffcc66; --text: #f0f0f0; --text-muted: #9494a5;
        --component-active-color-default: #ffdd95;
        --component-inactive-color: #666;
        --component-bg: #181818;
        --lineWidth: 0px;
    }
    * { -webkit-tap-highlight-color: transparent; box-sizing: border-box; }
    body { background: var(--bg); color: var(--text); font-family: 'Poppins', sans-serif; margin: 0; padding-bottom: 80px; overflow-x: hidden; }
    
    header { 
        background: rgba(5, 5, 5, 0.8); backdrop-filter: blur(20px); 
        padding: 15px 5%; display: flex; align-items: center; justify-content: center; 
        position: sticky; top:0; z-index:2000; transition: 0.4s;
    }
    .search-container { 
        width: 100%; max-width: 500px; position: relative; 
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .search-bar { 
        background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); 
        border-radius: 30px; padding: 10px 20px; display: flex; align-items: center; 
    }
    .search-bar input { 
        background: transparent; border: none; color: white; width: 100%; outline: none; font-family: inherit;
    }

    /* DOCKBAR / MOBILE MENU */
    .menu {
        position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
        background: var(--component-bg); border: 1px solid rgba(255,255,255,0.05);
        padding: 8px 15px; border-radius: 40px; display: flex; gap: 10px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.5); z-index: 3000;
        backdrop-filter: blur(15px);
    }
    .menu__item {
        background: transparent; border: none; color: var(--component-inactive-color);
        padding: 10px 15px; display: flex; align-items: center; gap: 8px;
        cursor: pointer; transition: 0.3s; position: relative; border-radius: 30px;
    }
    .menu__item.active { color: var(--primary); background: rgba(255,221,149,0.1); }
    .menu__icon { width: 20px; height: 20px; display: flex; align-items: center; }
    .menu__text { font-weight: 600; font-size: 14px; display: none; }
    .menu__item.active .menu__text { display: block; animation: fadeIn 0.3s; }
    
    @keyframes fadeIn { from { opacity: 0; transform: translateX(-5px); } to { opacity: 1; transform: translateX(0); } }
    
    .container { padding: 30px 5%; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 15px; }
    .card { background: var(--card); border-radius: 12px; overflow: hidden; text-decoration: none; color: inherit; border: 1px solid rgba(255,255,255,0.03); transition: 0.3s; }
    .card img { width: 100%; aspect-ratio: 2/3; object-fit: cover; }
    .card-info { padding: 10px; }
    .card-title { font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    
    @media (max-width: 600px) {
        .menu { bottom: 10px; width: 90%; justify-content: space-around; }
        .menu__item { padding: 10px; }
    }
</style>
<script src="https://unpkg.com/lucide@latest"></script>
"""

DOCBAR_HTML = """
<nav class="menu" id="dockbar">
    <button class="menu__item active" onclick="location.href='/explore'">
        <div class="menu__icon"><i data-lucide="home"></i></div>
        <strong class="menu__text">home</strong>
    </button>
    <button class="menu__item" onclick="location.href='/explore'">
        <div class="menu__icon"><i data-lucide="compass"></i></div>
        <strong class="menu__text">explore</strong>
    </button>
    <button class="menu__item" id="search-trigger">
        <div class="menu__icon"><i data-lucide="search"></i></div>
        <strong class="menu__text">search</strong>
    </button>
    <button class="menu__item" onclick="location.href='/tester'">
        <div class="menu__icon"><i data-lucide="settings"></i></div>
        <strong class="menu__text">tools</strong>
    </button>
</nav>
<script>
    lucide.createIcons();
    const items = document.querySelectorAll('.menu__item');
    items.forEach(item => {
        item.addEventListener('click', () => {
            items.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
        });
    });
</script>
"""

@app.get("/explore", response_class=HTMLResponse)
def explore_ui():
    d = get_home()
    cards = "".join([f'<a href="/anime-page?id={a["anime_id"]}" class="card"><img src="{a["image"]}" loading="lazy"><div class="card-info"><div class="card-title">{a["title"]}</div></div></a>' for a in d["latest_episodes"]])
    return f"""<!DOCTYPE html><html><head><title>Aniwatch</title>{SHARED_CSS}</head><body>
    <header>
        <div class="search-container">
            <div class="search-bar"><form action="/q" method="GET" style="width:100%"><input type="text" name="q" placeholder="Search anime..."></form></div>
        </div>
    </header>
    <div class="container"><h2>Trending</h2><div class="grid">{cards}</div></div>
    {DOCBAR_HTML}
    </body></html>"""

@app.get("/anime-page", response_class=HTMLResponse)
def anime_page_ui(id: str):
    a = get_anime(id); e = get_episodes(id)
    eps = "".join([f'<a href="/watch-page?id={id}&ep={x["ep_id"]}" class="ep-link" style="background:#222;color:#fff;padding:10px;border-radius:5px;text-decoration:none;text-align:center;">{x["number"]}</a>' for x in e["episodes"]])
    return f"""<!DOCTYPE html><html><head><title>{a['title']}</title>{SHARED_CSS}</head><body>
    <div class="container">
        <h1 style="color:var(--primary);">{a['title']}</h1>
        <p style="color:#aaa;">{a['description']}</p>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(50px,1fr));gap:10px;margin-top:30px;">{eps}</div>
    </div>
    {DOCBAR_HTML}
    </body></html>"""

@app.get("/watch-page", response_class=HTMLResponse)
def watch_page_ui(id: str, ep: str = None):
    cur_src = f"https://megaplay.buzz/stream/s-2/{ep}/sub" if ep else ""
    return f"""<!DOCTYPE html><html><head><title>Watch</title>{SHARED_CSS}</head><body>
    <div class="container">
        <div style="width:100%;aspect-ratio:16/9;background:#000;border-radius:15px;overflow:hidden;">
            <iframe src="{cur_src}" style="width:100%;height:100%;border:none;" allowfullscreen sandbox="allow-scripts allow-same-origin allow-forms"></iframe>
        </div>
    </div>
    {DOCBAR_HTML}
    </body></html>"""

@app.get("/q", response_class=HTMLResponse)
def search_ui(q: str):
    d = search_api(q)
    cards = "".join([f'<a href="/anime-page?id={a["anime_id"]}" class="card"><img src="{a["image"]}"><div class="card-info"><div class="card-title">{a["title"]}</div></div></a>' for a in d["results"]])
    return f"<!DOCTYPE html><html><head><title>Search</title>{SHARED_CSS}</head><body><div class=\"container\"><h2>Results</h2><div class=\"grid\">{cards}</div></div>{DOCBAR_HTML}</body></html>"

@app.get("/", response_class=HTMLResponse)
def read_root(): return explore_ui()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6969)

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
    t = el.find(['h3', 'h2', 'div'], class_=['film-name', 'film-title', 'desi-head-title']) or el.find('a', title=True)
    a = el.find('a', class_=['film-poster', 'film-poster-ahref']) or el.find('a', href=True)
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
        if fdi.find(class_=re.compile(r'tick')): continue
        text = fdi.get_text().strip()
        if not text or text in ["HD", "SD"]: continue
        if "m" in text or "h" in text: duration = text
        elif re.search(r'\d{4}', text): release_date = text
        elif not type_name: type_name = text
            
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

# --- API ENDPOINTS ---

@app.get("/home")
def get_home():
    try:
        r = requests.get(f"{BASE_URL}/home", headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')
        data = {"spotlight": [], "trending": [], "top_airing": [], "most_popular": [], "most_favorite": [], "latest_completed": [], "latest_episodes": [], "genres": []}
        for item in soup.select("#slider .swiper-slide"): data["spotlight"].append(parse_card(item))
        for item in soup.select("#trending-home .swiper-slide"): data["trending"].append(parse_card(item))
        for h in soup.select(".anif-block-header"):
            k = h.get_text().strip().lower().replace(" ", "_")
            if k in data:
                ul = h.find_next_sibling("div", class_="anif-block-ul")
                if ul:
                    for li in ul.find_all("li"): data[k].append(parse_card(li))
        for item in soup.find_all('div', class_=re.compile(r'flw-item')): data["latest_episodes"].append(parse_card(item))
        genres_set = set()
        for a in soup.find_all("a", href=True):
            if "/genre/" in a["href"]: genres_set.add(a.text.strip())
        data["genres"] = sorted(list(genres_set))
        return data
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/genre/{genre_name}")
def get_genre(genre_name: str, page: int = 1):
    try:
        r = requests.get(f"{BASE_URL}/genre/{genre_name}?page={page}", headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')
        return {"genre": genre_name, "results": [parse_card(i) for i in soup.find_all('div', class_=re.compile(r'flw-item'))]}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
def search_api(q: str = Query(...)):
    try:
        r = requests.get(f"{BASE_URL}/search?keyword={q}", headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')
        return {"results": [parse_card(i) for i in soup.find_all('div', class_=re.compile(r'flw-item'))]}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/anime/{anime_id}")
def get_anime(anime_id: str):
    try:
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
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/episodes/{anime_id}")
def get_episodes(anime_id: str):
    try:
        if not anime_id.isdigit():
            m = re.search(r'-(\d+)$', anime_id)
            if m: anime_id = m.group(1)
        r = requests.get(f"{BASE_URL}/ajax/v2/episode/list/{anime_id}", headers=AJAX_HEADERS)
        s = BeautifulSoup(r.json()["html"], 'html.parser')
        return {"episodes": [{"ep_id": a["data-id"], "number": a["data-number"], "title": a["title"]} for a in s.find_all("a", class_="ep-item")]}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/servers/{ep_id}")
def get_servers(ep_id: str):
    try:
        r = requests.get(f"{BASE_URL}/ajax/v2/episode/servers?episodeId={ep_id}", headers=AJAX_HEADERS)
        s = BeautifulSoup(r.json()["html"], 'html.parser')
        return {"servers": [{"server_id": d["data-id"], "name": d.get_text().strip(), "type": d["data-type"]} for d in s.find_all("div", class_="server-item")]}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/sources/{server_id}")
def get_sources(server_id: str):
    try: return requests.get(f"{BASE_URL}/ajax/v2/episode/sources?id={server_id}", headers=AJAX_HEADERS).json()
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/megaplay/{ep_id}")
def get_megaplay(ep_id: str):
    return {"episode_id": ep_id, "sub": f"https://megaplay.buzz/stream/s-2/{ep_id}/sub", "dub": f"https://megaplay.buzz/stream/s-2/{ep_id}/dub", "raw": f"https://megaplay.buzz/stream/s-2/{ep_id}/raw"}

# --- WEBSITE UI ---

SHARED_CSS = """
<style>
    :root { --bg: #0f0f0f; --card: #1a1a1a; --primary: #ffdd95; --text: #eee; --text-muted: #888; }
    body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; }
    header { background: rgba(24,24,24,0.9); backdrop-filter: blur(10px); padding: 15px 5%; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #333; position: sticky; top:0; z-index:1000; }
    .logo { color: var(--primary); font-size: 24px; font-weight: bold; text-decoration: none; }
    .nav-links a { color: var(--text); text-decoration: none; margin-left: 20px; font-weight: 500; }
    .nav-links a:hover { color: var(--primary); }
    .search-bar { background: #222; border: 1px solid #444; border-radius: 20px; padding: 5px 15px; display: flex; align-items: center; }
    .search-bar input { background: transparent; border: none; color: white; padding: 5px; outline: none; width: 200px; }
    .container { padding: 40px 5%; }
    .hero { height: 70vh; position: relative; overflow: hidden; background: #000; display: flex; align-items: flex-end; padding: 60px 5%; margin-bottom: 40px; }
    .hero-img { position: absolute; top:0; left:0; width:100%; height:100%; object-fit: cover; opacity: 0.4; }
    .hero-content { position: relative; z-index: 10; max-width: 800px; }
    .hero-title { font-size: 48px; color: var(--primary); margin-bottom: 15px; text-shadow: 0 2px 10px rgba(0,0,0,0.8); }
    .hero-desc { color: #ccc; margin-bottom: 25px; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.6; font-size: 18px; }
    .btn-main { background: var(--primary); color: black; padding: 12px 30px; border-radius: 5px; text-decoration: none; font-weight: bold; margin-right: 15px; display: inline-block; transition: 0.3s; }
    .btn-main:hover { transform: scale(1.05); }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; }
    .card { background: var(--card); border-radius: 8px; overflow: hidden; transition: transform 0.2s; text-decoration: none; color: inherit; position: relative; display: flex; flex-direction: column; border: 1px solid #222; }
    .card:hover { transform: translateY(-5px); border: 1px solid var(--primary); }
    .card img { width: 100%; aspect-ratio: 2/3; object-fit: cover; }
    .card-info { padding: 12px; }
    .card-title { font-size: 14px; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .badge { background: var(--primary); color: black; font-size: 10px; padding: 2px 5px; border-radius: 3px; font-weight: bold; margin-right: 5px; }
    .detail-container { display: flex; gap: 40px; }
    .detail-poster { width: 300px; flex-shrink: 0; }
    .detail-poster img { width: 100%; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.5); }
    .meta-item { margin-bottom: 10px; }
    .meta-key { color: var(--primary); font-weight: bold; width: 120px; display: inline-block; }
    .watch-layout { display: grid; grid-template-columns: 1fr 350px; gap: 30px; }
    .player-area { width: 100%; aspect-ratio: 16/9; background: #000; border-radius: 8px; box-shadow: 0 0 30px rgba(0,0,0,0.5); }
    .episodes-card { background: #181818; border-radius: 8px; padding: 20px; height: fit-content; max-height: 80vh; overflow-y: auto; border: 1px solid #333; }
    .ep-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(50px, 1fr)); gap: 8px; }
    .ep-link { background: #2a2a2a; color: white; text-decoration: none; padding: 10px; border-radius: 4px; text-align: center; font-size: 12px; transition: 0.2s; border: 1px solid #444; }
    .ep-link:hover, .ep-link.active { background: var(--primary); color: #000; border-color: var(--primary); }
    @media (max-width: 900px) { .detail-container, .watch-layout { flex-direction: column; display: block; } .detail-poster { width: 100%; max-width: 300px; margin-bottom: 30px; } .episodes-card { margin-top: 30px; } .hero-title { font-size: 32px; } }
</style>
"""

HEADER_HTML = """
<header>
    <a href="/explore" class="logo">AniwatchTV</a>
    <div class="search-bar"><form action="/q" method="GET"><input type="text" name="q" placeholder="Search anime..."></form></div>
    <nav class="nav-links"><a href="/explore">Home</a><a href="/tester">Tester</a><a href="/">API</a></nav>
</header>
"""

@app.get("/explore", response_class=HTMLResponse)
def explore_ui():
    try:
        data = get_home()
        hero = data["spotlight"][0] if data["spotlight"] else None
        hero_html = ""
        if hero:
            hero_html = f'''
            <div class="hero">
                <img src="{hero["image"]}" class="hero-img">
                <div class="hero-content">
                    <h1 class="hero-title">{hero["title"]}</h1>
                    <p class="hero-desc">{hero["description"]}</p>
                    <div style="margin-bottom: 30px;">
                        <span class="badge">{hero.get("type", "")}</span>
                        <span class="badge">{hero.get("duration", "")}</span>
                        <span class="badge">SUB {hero.get("sub", "")}</span>
                    </div>
                    <a href="/anime-page?id={hero["anime_id"]}" class="btn-main">View Details</a>
                    <a href="/watch-page?id={hero["anime_id"]}" class="btn-main" style="background:#fff; color:black;">Watch Now</a>
                </div>
            </div>'''
        cards_html = "".join([f'<a href="/anime-page?id={a["anime_id"]}" class="card"><img src="{a["image"]}" loading="lazy"><div class="card-info"><div class="card-title">{a["title"]}</div><div class="card-meta">{f"<span class=\"badge\">SUB {a['sub']}</span>" if a["sub"] else ""}<span>{a["type"]}</span></div></div></a>' for a in data["latest_episodes"]])
        return f"<!DOCTYPE html><html><head><title>AniwatchTV - Home</title>{SHARED_CSS}</head><body>{HEADER_HTML}{hero_html}<div class=\"container\"><h2>Latest Episodes</h2><div class=\"grid\">{cards_html}</div></div></body></html>"
    except Exception as e: return HTMLResponse(f"Error: {e}", status_code=500)

@app.get("/anime-page", response_class=HTMLResponse)
def anime_page_ui(id: str):
    try:
        anime = get_anime(id)
        episodes = get_episodes(id)
        eps_html = "".join([f'<a href="/watch-page?id={id}&ep={e["ep_id"]}" class="ep-link">{e["number"]}</a>' for e in episodes["episodes"]])
        details_html = "".join([f'<div class="meta-item"><span class="meta-key">{k.capitalize()}:</span> <span>{v}</span></div>' for k, v in anime["details"].items()])
        return f"<!DOCTYPE html><html><head><title>{anime['title']}</title>{SHARED_CSS}</head><body>{HEADER_HTML}<div class=\"container\"><div class=\"detail-container\"><div class=\"detail-poster\"><img src=\"{anime['image']}\"></div><div class=\"detail-info\"><h1 style=\"color:var(--primary); font-size:42px;\">{anime['title']}</h1><p style=\"font-size:18px; line-height:1.6; color:#ccc;\">{anime['description']}</p><div style=\"margin: 30px 0; background:#181818; padding:20px; border-radius:8px;\">{details_html}</div><div class=\"episodes-section\"><h2 style=\"margin-bottom:20px;\">Episodes</h2><div class=\"ep-grid\">{eps_html}</div></div></div></div></div></body></html>"
    except Exception as e: return HTMLResponse(f"Error: {e}", status_code=500)

@app.get("/watch-page", response_class=HTMLResponse)
def watch_page_ui(id: str, ep: str = None):
    try:
        anime = get_anime(id)
        episodes = get_episodes(id)
        current_ep_id = ep if ep else (episodes["episodes"][0]["ep_id"] if episodes["episodes"] else None)
        eps_html = ""
        next_ep_url = ""
        found_current = False
        for e in episodes["episodes"]:
            active = "active" if e["ep_id"] == current_ep_id else ""
            eps_html += f'<a href="/watch-page?id={id}&ep={e["ep_id"]}" class="ep-link {active}">{e["number"]}</a>'
            if found_current: next_ep_url = f"/watch-page?id={id}&ep={e['ep_id']}"; found_current = False
            if e["ep_id"] == current_ep_id: found_current = True
        stream_url = f"https://megaplay.buzz/stream/s-2/{current_ep_id}/sub" if current_ep_id else ""
        return f"<!DOCTYPE html><html><head><title>Watching {anime['title']}</title>{SHARED_CSS}</head><body>{HEADER_HTML}<div class=\"container\"><div class=\"watch-layout\"><div class=\"main-player\"><div class=\"player-area\"><iframe src=\"{stream_url}\" id=\"player\" style=\"width:100%;height:100%;border:none;\" allowfullscreen=\"true\" sandbox=\"allow-scripts allow-same-origin allow-forms\"></iframe></div><h1 style=\"color:var(--primary); margin-top:25px;\">{anime['title']}</h1><p style=\"color:#aaa; line-height:1.6;\">{anime['description'][:500]}...</p></div><div class=\"episodes-card\"><h3 style=\"margin-top:0; border-bottom:1px solid #333; padding-bottom:10px; color:var(--primary);\">Episodes</h3><div class=\"ep-grid\">{eps_html}</div></div></div></div><script>const nextUrl = \"{next_ep_url}\"; window.addEventListener(\"message\", function(event) {{ let data = event.data; if (typeof data === \"string\") {{ try {{ data = JSON.parse(data); }} catch(e) {{}} }} if ((data.event === \"complete\" || data.type === \"complete\") && nextUrl) {{ window.location.href = nextUrl; }} }});</script></body></html>"
    except Exception as e: return HTMLResponse(f"Error: {e}", status_code=500)

@app.get("/q", response_class=HTMLResponse)
def search_ui_results(q: str):
    try:
        data = search_api(q)
        cards_html = "".join([f'<a href="/anime-page?id={a["anime_id"]}" class="card"><img src="{a["image"]}"><div class="card-info"><div class="card-title">{a["title"]}</div></div></a>' for a in data["results"]])
        return f"<!DOCTYPE html><html><head><title>Search: {q}</title>{SHARED_CSS}</head><body>{HEADER_HTML}<div class=\"container\"><h2>Results for: {q}</h2><div class=\"grid\">{cards_html}</div></div></body></html>"
    except Exception as e: return HTMLResponse(f"Error: {e}", status_code=500)

@app.get("/", response_class=HTMLResponse)
def read_root():
    return HTMLResponse("<!DOCTYPE html><html><head><title>AniwatchTV Unofficial</title><style>body { font-family: 'Segoe UI', sans-serif; margin: 0; background: #0f0f0f; color: #eee; display: flex; align-items: center; justify-content: center; height: 100vh; } .box { text-align: center; background: #181818; padding: 50px; border-radius: 12px; border: 1px solid #333; } .btn { display: inline-block; padding: 15px 40px; background: #ffdd95; color: black; border-radius: 8px; font-weight: bold; text-decoration: none; font-size: 20px; }</style></head><body><div class=\"box\"><h1>AniwatchTV</h1><a href=\"/explore\" class=\"btn\">Enter Website</a></div></body></html>")

@app.get("/tester", response_class=HTMLResponse)
def tester_ui():
    return HTMLResponse("<!DOCTYPE html><html><head><title>MegaPlay Tester</title><style>body { font-family: 'Segoe UI', sans-serif; margin: 0; background: #0f0f0f; color: #eee; display: flex; height: 100vh; } .sidebar { width: 350px; background: #181818; border-right: 1px solid #333; } .main { flex: 1; background: #000; } #log { padding: 20px; font-size: 12px; font-family: monospace; overflow-y: auto; height: 70%; }</style></head><body><div class=\"sidebar\"><div style=\"padding:20px;\"><h3>Tester</h3><input id=u style=\"width:100%; padding:8px; background:#222; color:#fff; border:1px solid #444;\"><button onclick=\"f.src=u.value\" style=\"margin-top:10px; width:100%; padding:10px;\">Load</button></div><div id=log>Logs...</div></div><div class=\"main\"><iframe id=f style=\"width:100%;height:100%;border:none;\" allowfullscreen sandbox=\"allow-scripts allow-same-origin allow-forms\"></iframe></div><script>window.addEventListener(\"message\", (e) => {{ const d = document.createElement(\"div\"); d.innerText = JSON.stringify(e.data); document.getElementById(\"log\").prepend(d); }});</script></body></html>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6969)

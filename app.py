from fastapi import FastAPI, HTTPException, Query, Path, Request
from fastapi.responses import HTMLResponse
import requests
from bs4 import BeautifulSoup
import re
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal

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
        url = f"{BASE_URL}/genre/{genre_name}?page={page}"
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        items = soup.find_all('div', class_=re.compile(r'flw-item'))
        return {
            "genre": genre_name,
            "page": page,
            "results": [parse_card(i) for i in items]
        }
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
    return {
        "episode_id": ep_id,
        "sub": f"https://megaplay.buzz/stream/s-2/{ep_id}/sub",
        "dub": f"https://megaplay.buzz/stream/s-2/{ep_id}/dub",
        "raw": f"https://megaplay.buzz/stream/s-2/{ep_id}/raw"
    }

# --- WEBSITE UI ENDPOINTS ---

SHARED_CSS = """
<style>
    :root { --bg: #0f0f0f; --card: #1a1a1a; --primary: #ffdd95; --text: #eee; --text-muted: #888; }
    body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; }
    header { background: #181818; padding: 15px 5%; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #333; position: sticky; top:0; z-index:100; }
    .logo { color: var(--primary); font-size: 24px; font-weight: bold; text-decoration: none; }
    .nav-links a { color: var(--text); text-decoration: none; margin-left: 20px; font-weight: 500; }
    .nav-links a:hover { color: var(--primary); }
    .search-bar { background: #222; border: 1px solid #444; border-radius: 20px; padding: 5px 15px; display: flex; align-items: center; }
    .search-bar input { background: transparent; border: none; color: white; padding: 5px; outline: none; width: 200px; }
    .container { padding: 40px 5%; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; }
    .card { background: var(--card); border-radius: 8px; overflow: hidden; transition: transform 0.2s; text-decoration: none; color: inherit; position: relative; }
    .card:hover { transform: translateY(-5px); border: 1px solid var(--primary); }
    .card img { width: 100%; aspect-ratio: 2/3; object-fit: cover; }
    .card-info { padding: 10px; }
    .card-title { font-size: 14px; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .card-meta { font-size: 12px; color: var(--text-muted); margin-top: 5px; }
    .badge { background: var(--primary); color: black; font-size: 10px; padding: 2px 5px; border-radius: 3px; font-weight: bold; margin-right: 5px; }
    h2 { border-left: 4px solid var(--primary); padding-left: 15px; margin-bottom: 30px; }
    .watch-container { display: flex; flex-direction: column; gap: 20px; }
    .player-box { width: 100%; aspect-ratio: 16/9; background: black; border-radius: 8px; overflow: hidden; }
    .episodes-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(60px, 1fr)); gap: 10px; margin-top: 20px; }
    .ep-btn { background: #222; border: 1px solid #444; color: white; padding: 10px; border-radius: 4px; text-align: center; text-decoration: none; font-size: 14px; }
    .ep-btn:hover, .ep-btn.active { background: var(--primary); color: black; border-color: var(--primary); }
    .server-list { display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap; }
    .srv-btn { background: #333; padding: 8px 15px; border-radius: 4px; cursor: pointer; border: 1px solid #555; }
    .srv-btn.active { background: var(--primary); color: black; }
</style>
"""

HEADER_HTML = """
<header>
    <a href="/explore" class="logo">AniwatchTV</a>
    <div class="search-bar">
        <form action="/q" method="GET">
            <input type="text" name="q" placeholder="Search anime...">
        </form>
    </div>
    <nav class="nav-links">
        <a href="/explore">Explore</a>
        <a href="/tester">Tester</a>
        <a href="/">API</a>
    </nav>
</header>
"""

@app.get("/explore", response_class=HTMLResponse)
def explore():
    try:
        data = get_home()
        cards_html = ""
        for anime in data["latest_episodes"]:
            cards_html += f'''
            <a href="/watch-page?id={anime["anime_id"]}" class="card">
                <img src="{anime["image"]}" loading="lazy">
                <div class="card-info">
                    <div class="card-title">{anime["title"]}</div>
                    <div class="card-meta">
                        {f'<span class="badge">SUB {anime["sub"]}</span>' if anime["sub"] else ''}
                        {f'<span class="badge">DUB {anime["dub"]}</span>' if anime["dub"] else ''}
                        <span>{anime["type"]}</span>
                    </div>
                </div>
            </a>
            '''
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Explore Anime</title>{SHARED_CSS}</head>
        <body>
            {HEADER_HTML}
            <div class="container">
                <h2>Latest Episodes</h2>
                <div class="grid">{cards_html}</div>
            </div>
        </body>
        </html>
        """
    except Exception as e: return HTMLResponse(f"Error: {e}")

@app.get("/q", response_class=HTMLResponse)
def search_ui(q: str = Query(...)):
    try:
        data = search_api(q)
        cards_html = ""
        for anime in data["results"]:
            cards_html += f'''
            <a href="/watch-page?id={anime["anime_id"]}" class="card">
                <img src="{anime["image"]}" loading="lazy">
                <div class="card-info">
                    <div class="card-title">{anime["title"]}</div>
                    <div class="card-meta">
                        <span>{anime["type"]}</span>
                    </div>
                </div>
            </a>
            '''
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Search: {q}</title>{SHARED_CSS}</head>
        <body>
            {HEADER_HTML}
            <div class="container">
                <h2>Search Results for: {q}</h2>
                <div class="grid">{cards_html}</div>
            </div>
        </body>
        </html>
        """
    except Exception as e: return HTMLResponse(f"Error: {e}")

@app.get("/watch-page", response_class=HTMLResponse)
def watch_page(id: str, ep: str = None):
    try:
        anime = get_anime(id)
        episodes = get_episodes(id)
        
        current_ep_id = ep if ep else (episodes["episodes"][0]["ep_id"] if episodes["episodes"] else None)
        
        eps_html = ""
        for e in episodes["episodes"]:
            active = "active" if e["ep_id"] == current_ep_id else ""
            eps_html += f'<a href="/watch-page?id={id}&ep={e["ep_id"]}" class="ep-btn {active}">{e["number"]}</a>'
            
        player_html = ""
        if current_ep_id:
            # Default to megaplay for easiest embedding
            stream_url = f"https://megaplay.buzz/stream/s-2/{current_ep_id}/sub"
            player_html = f'<iframe src="{stream_url}" id="player" class="player-box" allowfullscreen="true" sandbox="allow-scripts allow-same-origin allow-forms"></iframe>'

        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Watching {anime["title"]}</title>{SHARED_CSS}</head>
        <body>
            {HEADER_HTML}
            <div class="container">
                <div class="watch-container">
                    {player_html}
                    <div class="anime-info">
                        <h1 style="color:var(--primary);">{anime["title"]}</h1>
                        <p style="color:var(--text-muted);">{anime["description"][:300]}...</p>
                    </div>
                    <div class="episodes-section">
                        <h3>Episodes</h3>
                        <div class="episodes-grid">{eps_html}</div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    except Exception as e: return HTMLResponse(f"Error: {e}")

@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AniwatchTV Unofficial API</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; line-height: 1.6; margin: 0; background: #0f0f0f; color: #eee; }
            .container { max-width: 900px; margin: 40px auto; padding: 20px; background: #181818; border-radius: 8px; border: 1px solid #333; }
            h1 { color: #ffdd95; border-bottom: 2px solid #ffdd95; padding-bottom: 10px; }
            h2 { color: #ffdd95; margin-top: 30px; }
            code { background: #222; padding: 2px 6px; border-radius: 4px; color: #ffdd95; font-family: monospace; }
            .endpoint { margin-bottom: 20px; padding: 15px; background: #222; border-radius: 5px; }
            .method { font-weight: bold; color: #2ecc71; margin-right: 10px; }
            .path { font-weight: bold; color: #3498db; }
            .desc { margin-top: 5px; color: #ccc; }
            a { color: #ffdd95; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .btn { display: inline-block; padding: 10px 20px; background: #ffdd95; color: black; border-radius: 5px; font-weight: bold; margin-top: 20px; margin-right: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AniwatchTV Unofficial API</h1>
            <p>Welcome to the unofficial scraper API and website for AniwatchTV.</p>
            
            <a href="/explore" class="btn">Launch Website</a>
            <a href="/tester" class="btn" style="background:#444; color:white;">Open Iframe Tester</a>

            <h2>Core Endpoints</h2>
            
            <div class="endpoint">
                <span class="method">GET</span><span class="path">/home</span>
                <div class="desc">Fetches Spotlights, Trending, Genres, and Latest Episodes.</div>
            </div>

            <div class="endpoint">
                <span class="method">GET</span><span class="path">/genre/{name}</span>
                <div class="desc">Fetch anime list for a specific genre (e.g. action, shounen).</div>
            </div>

            <div class="endpoint">
                <span class="method">GET</span><span class="path">/search?q={query}</span>
                <div class="desc">Search for anime by title.</div>
            </div>

            <div class="endpoint">
                <span class="method">GET</span><span class="path">/anime/{id_or_slug}</span>
                <div class="desc">Get full details, metadata, and season list.</div>
            </div>

            <div class="endpoint">
                <span class="method">GET</span><span class="path">/episodes/{anime_id}</span>
                <div class="desc">Get episode list for a series.</div>
            </div>

            <div class="endpoint">
                <span class="method">GET</span><span class="path">/servers/{ep_id}</span>
                <div class="desc">List available streaming servers.</div>
            </div>

            <div class="endpoint">
                <span class="method">GET</span><span class="path">/sources/{server_id}</span>
                <div class="desc">Get the final embed link.</div>
            </div>

            <div class="endpoint">
                <span class="method">GET</span><span class="path">/megaplay/{ep_id}</span>
                <div class="desc">Direct megaplay.buzz iframe URLs.</div>
            </div>

            <p style="margin-top: 40px; font-size: 12px; color: #666;">
                Note: This API is for educational purposes. All content rights belong to the original owners.
            </p>
        </div>
    </body>
    </html>
    """

@app.get("/tester", response_class=HTMLResponse)
def tester():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Aniwatch API - Iframe Tester</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; background: #0f0f0f; color: #eee; display: flex; height: 100vh; overflow: hidden; }
            .sidebar { width: 350px; background: #181818; border-right: 1px solid #333; display: flex; flex-direction: column; }
            .main { flex: 1; display: flex; flex-direction: column; background: #000; position: relative; }
            .header { padding: 20px; border-bottom: 1px solid #333; }
            .input-group { display: flex; gap: 10px; margin-top: 10px; }
            input { flex: 1; padding: 10px; border-radius: 4px; border: 1px solid #444; background: #222; color: white; }
            button { padding: 10px 20px; border-radius: 4px; border: none; background: #ffdd95; color: black; font-weight: bold; cursor: pointer; }
            button:hover { background: #ffcc66; }
            #log { flex: 1; overflow-y: auto; padding: 20px; font-size: 13px; font-family: monospace; border-top: 1px solid #333; }
            .log-entry { margin-bottom: 8px; border-bottom: 1px solid #222; padding-bottom: 4px; }
            .log-time { color: #888; margin-right: 10px; }
            .log-event { color: #ffdd95; font-weight: bold; }
            .log-data { color: #aaa; }
            iframe { width: 100%; height: 100%; border: none; }
            .badge { padding: 2px 6px; border-radius: 3px; font-size: 10px; text-transform: uppercase; margin-left: 5px; }
            .badge-info { background: #3498db; color: white; }
            .badge-success { background: #2ecc71; color: white; }
            .badge-error { background: #e74c3c; color: white; }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="header">
                <h3>MegaPlay Tester</h3>
                <p style="font-size: 12px; color: #888;">Paste your source link or megaplay URL below.</p>
                <div class="input-group">
                    <input type="text" id="u" placeholder="https://megaploud.blog/...">
                    <button onclick="loadUrl()">Load</button>
                </div>
            </div>
            <div id="log">
                <div style="color: #ffdd95; border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 10px;">Event Log (PostMessage)</div>
            </div>
        </div>
        <div class="main">
            <iframe id="f" allowfullscreen="true" sandbox="allow-scripts allow-same-origin allow-forms" src="about:blank"></iframe>
        </div>

        <script>
            function addLog(event, data) {
                const log = document.getElementById('log');
                const div = document.createElement('div');
                div.className = 'log-entry';
                const time = new Date().toLocaleTimeString();
                
                let badgeClass = 'badge-info';
                if(event === 'complete') badgeClass = 'badge-success';
                if(event === 'error') badgeClass = 'badge-error';
                
                div.innerHTML = `<span class="log-time">${time}</span><span class="log-event">${event}</span><span class="badge ${badgeClass}">${data.channel || 'api'}</span><br><span class="log-data">${JSON.stringify(data, null, 2)}</span>`;
                log.insertBefore(div, log.firstChild.nextSibling);
            }

            function loadUrl() {
                const url = document.getElementById('u').value;
                if(url) {
                    const log = document.getElementById('log');
                    log.innerHTML = '<div style="color: #ffdd95; border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 10px;">Event Log (PostMessage)</div>';
                    document.getElementById('f').src = url;
                    addLog('loading', { url: url });
                }
            }

            window.addEventListener("message", function (event) {
                let data = event.data;
                if (typeof data === "string") {
                    try { data = JSON.parse(data); } catch (e) { return; }
                }

                if (data.channel === "megacloud" || data.type === "watching-log" || data.event) {
                    addLog(data.event || data.type || 'message', data);
                }
            });
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6969)

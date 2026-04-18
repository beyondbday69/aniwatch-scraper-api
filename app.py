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
            .btn { display: inline-block; padding: 10px 20px; background: #ffdd95; color: black; border-radius: 5px; font-weight: bold; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AniwatchTV Unofficial API</h1>
            <p>Welcome to the unofficial scraper API for AniwatchTV. Use the endpoints below to fetch data.</p>
            
            <a href="/tester" class="btn">Open Iframe Tester</a>

            <h2>Core Endpoints</h2>
            
            <div class="endpoint">
                <span class="method">GET</span><span class="path">/home</span>
                <div class="desc">Fetches everything from the homepage: Spotlights, Trending, Genres, and Latest Episodes.</div>
            </div>

            <div class="endpoint">
                <span class="method">GET</span><span class="path">/search?q={query}</span>
                <div class="desc">Search for anime by title. Returns full slugs as <code>anime_id</code>.</div>
            </div>

            <div class="endpoint">
                <span class="method">GET</span><span class="path">/anime/{id_or_slug}</span>
                <div class="desc">Get full details, metadata, and season list for a specific anime.</div>
            </div>

            <div class="endpoint">
                <span class="method">GET</span><span class="path">/episodes/{anime_id}</span>
                <div class="desc">Get all episodes and their internal IDs for a series.</div>
            </div>

            <div class="endpoint">
                <span class="method">GET</span><span class="path">/servers/{ep_id}</span>
                <div class="desc">List available streaming servers (VidSrc, MegaCloud, etc.) for an episode.</div>
            </div>

            <div class="endpoint">
                <span class="method">GET</span><span class="path">/sources/{server_id}</span>
                <div class="desc">Get the final iframe embed link from an internal server ID.</div>
            </div>

            <div class="endpoint">
                <span class="method">GET</span><span class="path">/megaplay/{ep_id}</span>
                <div class="desc">Direct utility to get megaplay.buzz iframe URLs (sub/dub/raw).</div>
            </div>

            <p style="margin-top: 40px; font-size: 12px; color: #666;">
                Note: This API is for educational purposes. All content rights belong to the original owners.
            </p>
        </div>
    </body>
    </html>
    """

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

                // MegaCloud / MegaPlay Channel
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

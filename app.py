from fastapi import FastAPI, HTTPException, Query, Path, Request
from fastapi.responses import HTMLResponse, JSONResponse
import requests
from bs4 import BeautifulSoup
import re
import json
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal
from cachetools import TTLCache
import time

app = FastAPI(title="AniwatchTV Unofficial API")

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

# Cache: 50 items, expires in 10 minutes
cache = TTLCache(maxsize=100, ttl=600)

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
        if fdi.find(class_=re.compile(r'tick')): continue
        text = fdi.get_text().strip()
        if not text or text in ["HD", "SD"]: continue
        if "m" in text or "h" in text: duration = text
        elif re.search(r'\d{4}', text): release_date = text
        elif not type_name: type_name = text
            
    desc_tag = el.find('div', class_='desi-description')
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
        "description": desc_tag.get_text().strip() if desc_tag else ""
    }

def beauty_json_response(request: Request, data: dict):
    # Detect browser request
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        json_str = json.dumps(data, indent=4)
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>API Response</title>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
            <style>
                body {{ background: #0d1117; margin: 0; padding: 20px; color: #c9d1d9; font-family: monospace; }}
                .container {{ max-width: 1200px; margin: 0 auto; position: relative; }}
                pre {{ border-radius: 8px; padding: 20px !important; background: #161b22 !important; border: 1px solid #30363d; overflow: auto; }}
                .top-bar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
                .badge {{ background: #238636; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }}
                .btn-copy {{ background: #21262d; border: 1px solid #30363d; color: #c9d1d9; padding: 5px 10px; border-radius: 6px; cursor: pointer; }}
                .btn-copy:hover {{ background: #30363d; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="top-bar">
                    <div><span class="badge">JSON</span> <small>application/json</small></div>
                    <button class="btn-copy" onclick="copyJson()">Copy JSON</button>
                </div>
                <pre><code class="language-json" id="jsonCode">{json_str}</code></pre>
            </div>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-json.min.js"></script>
            <script>
                function copyJson() {{
                    const code = document.getElementById('jsonCode').innerText;
                    navigator.clipboard.writeText(code);
                    alert('Copied to clipboard!');
                }}
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
    return JSONResponse(content=data)

@app.get("/", response_class=HTMLResponse)
def read_root():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AniwatchTV API</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root { --primary: #ffdd95; --bg: #0d1117; --card: #161b22; --border: #30363d; --text: #c9d1d9; }
            body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; margin: 0; display: flex; align-items: center; justify-content: center; height: 100vh; }
            .card { background: var(--card); padding: 40px; border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 8px 24px rgba(0,0,0,0.3); text-align: center; max-width: 450px; width: 90%; }
            .logo { font-size: 48px; color: var(--primary); margin-bottom: 20px; }
            h1 { font-size: 24px; margin: 0 0 10px 0; color: #fff; }
            p { color: #8b949e; margin-bottom: 30px; line-height: 1.5; }
            .links { display: flex; flex-direction: column; gap: 12px; }
            .btn { text-decoration: none; padding: 12px; border-radius: 6px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 10px; transition: 0.2s; }
            .btn-primary { background: var(--primary); color: #0d1117; }
            .btn-primary:hover { background: #ffe4a8; transform: translateY(-2px); }
            .btn-outline { border: 1px solid var(--border); color: #fff; background: #21262d; }
            .btn-outline:hover { background: #30363d; border-color: #8b949e; }
            .footer { margin-top: 30px; font-size: 12px; color: #484f58; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="logo"><i class="fas fa-bolt"></i></div>
            <h1>AniwatchTV API</h1>
            <p>Fast, cached, and beautiful unofficial API for anime metadata and streaming sources.</p>
            <div class="links">
                <a href="/docs" class="btn btn-primary"><i class="fas fa-book"></i> Interactive API Docs</a>
                <a href="/home" class="btn btn-outline"><i class="fas fa-home"></i> Explore Home Data</a>
                <a href="/tester" class="btn btn-outline"><i class="fas fa-vial"></i> Iframe Event Tester</a>
                <a href="https://github.com/beyondbday69/aniwatch-scraper-api" class="btn btn-outline" target="_blank">
                    <i class="fab fa-github"></i> GitHub Repository
                </a>
            </div>
            <div class="footer">v2.0.0 • High Performance Scraper</div>
        </div>
    </body>
    </html>
    """)

@app.get("/home")
def get_home(request: Request):
    if "home" in cache: return beauty_json_response(request, cache["home"])
    try:
        r = requests.get(f"{BASE_URL}/home", headers=HEADERS)
        r.raise_for_status()
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
        cache["home"] = data
        return beauty_json_response(request, data)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/popular")
def get_popular(request: Request):
    if "popular" in cache: return beauty_json_response(request, cache["popular"])
    r = requests.get(f"{BASE_URL}/home", headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    data = {"results": [parse_card(i) for i in soup.find_all('div', class_=re.compile(r'flw-item'))]}
    cache["popular"] = data
    return beauty_json_response(request, data)

@app.get("/search")
def search(request: Request, q: str = Query(...)):
    cache_key = f"search_{q}"
    if cache_key in cache: return beauty_json_response(request, cache[cache_key])
    r = requests.get(f"{BASE_URL}/search?keyword={q}", headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    data = {"results": [parse_card(i) for i in soup.find_all('div', class_=re.compile(r'flw-item'))]}
    cache[cache_key] = data
    return beauty_json_response(request, data)

@app.get("/anime/{anime_id}")
def get_anime(request: Request, anime_id: str):
    if f"anime_{anime_id}" in cache: return beauty_json_response(request, cache[f"anime_{anime_id}"])
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
    data = {
        "anime_id": anime_id,
        "title": soup.find('h2', class_='film-name').get_text().strip() if soup.find('h2', class_='film-name') else "Unknown",
        "description": soup.find('div', class_='film-description').get_text().strip() if soup.find('div', class_='film-description') else "",
        "image": soup.find('img', class_='film-poster-img').get('src') if soup.find('img', class_='film-poster-img') else "",
        "details": details,
        "seasons": [{"title": a.find('div', class_='title').get_text().strip(), "anime_id": get_slug(a.get('href'))} for a in soup.select(".os-list a")] if soup.select(".os-list a") else []
    }
    cache[f"anime_{anime_id}"] = data
    return beauty_json_response(request, data)

@app.get("/episodes/{anime_id}")
def get_episodes(request: Request, anime_id: str):
    if f"eps_{anime_id}" in cache: return beauty_json_response(request, cache[f"eps_{anime_id}"])
    if not anime_id.isdigit():
        m = re.search(r'-(\d+)$', anime_id)
        if m: anime_id = m.group(1)
    r = requests.get(f"{BASE_URL}/ajax/v2/episode/list/{anime_id}", headers=AJAX_HEADERS)
    s = BeautifulSoup(r.json()["html"], 'html.parser')
    data = {"episodes": [{"ep_id": a["data-id"], "number": a["data-number"], "title": a["title"]} for a in s.find_all("a", class_="ep-item")]}
    cache[f"eps_{anime_id}"] = data
    return beauty_json_response(request, data)

@app.get("/servers/{ep_id}")
def get_servers(request: Request, ep_id: str):
    r = requests.get(f"{BASE_URL}/ajax/v2/episode/servers?episodeId={ep_id}", headers=AJAX_HEADERS)
    s = BeautifulSoup(r.json()["html"], 'html.parser')
    return beauty_json_response(request, {"servers": [{"server_id": d["data-id"], "name": d.get_text().strip(), "type": d["data-type"]} for d in soup.find_all("div", class_="server-item")]})

@app.get("/megaplay/{ep_id}")
def get_megaplay(request: Request, ep_id: str):
    return beauty_json_response(request, {
        "episode_id": ep_id,
        "sub": f"https://megaplay.buzz/stream/s-2/{ep_id}/sub",
        "dub": f"https://megaplay.buzz/stream/s-2/{ep_id}/dub",
        "raw": f"https://megaplay.buzz/stream/s-2/{ep_id}/raw"
    })

@app.get("/sources/{server_id}")
def get_sources(request: Request, server_id: str):
    return beauty_json_response(request, requests.get(f"{BASE_URL}/ajax/v2/episode/sources?id={server_id}", headers=AJAX_HEADERS).json())

@app.get("/tester", response_class=HTMLResponse)
def tester():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MegaPlay & Iframe Tester</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body style="background:#0d1117; color:#c9d1d9; font-family:sans-serif; margin:0; padding:20px; display:flex; flex-direction:column; height:100vh; box-sizing:border-box;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h2 style="margin:0; color:#ffdd95;"><i class="fas fa-flask"></i> MegaPlay Tester</h2>
            <a href="/" style="color:#8b949e; text-decoration:none;"><i class="fas fa-arrow-left"></i> Back Home</a>
        </div>
        <div style="display:flex; gap:10px; margin-bottom:20px;">
            <input type="text" id="url" style="flex:1; padding:12px; background:#161b22; border:1px solid #30363d; border-radius:6px; color:#fff;" placeholder="Paste Megaplay URL...">
            <button onclick="document.getElementById('f').src=document.getElementById('url').value" style="padding:10px 25px; border-radius:6px; border:none; background:#ffdd95; color:#0d1117; cursor:pointer; font-weight:bold;">Load Player</button>
        </div>
        <div style="display:flex; flex:1; gap:20px; min-height:0;">
            <div style="flex:2; background:#000; border-radius:8px; border:1px solid #30363d; overflow:hidden;">
                <iframe id="f" style="width:100%; height:100%; border:none;" allowfullscreen></iframe>
            </div>
            <div style="flex:1; background:#161b22; padding:20px; border-radius:8px; border:1px solid #30363d; display:flex; flex-direction:column;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                    <h3 style="margin:0;"><i class="fas fa-terminal"></i> Event Logs</h3>
                    <button onclick="document.getElementById('logs').innerHTML=''" style="background:transparent; border:1px solid #30363d; color:#8b949e; padding:5px 10px; border-radius:4px; cursor:pointer;">Clear</button>
                </div>
                <div id="logs" style="flex:1; overflow-y:auto; font-family:monospace; font-size:12px;"></div>
            </div>
        </div>
        <script>
            function log(msg, color) {
                const logs = document.getElementById('logs');
                const div = document.createElement('div');
                div.style.color = color || '#8DFFBF';
                div.style.background = '#0d1117';
                div.style.padding = '8px';
                div.style.borderRadius = '4px';
                div.style.marginBottom = '8px';
                div.style.border = '1px solid #30363d';
                const time = new Date().toLocaleTimeString();
                div.innerText = `[${time}] ` + (typeof msg === 'object' ? JSON.stringify(msg, null, 2) : msg);
                logs.prepend(div);
            }
            window.addEventListener('message', function (e) {
                let data = e.data;
                if (typeof data === 'string') { try { data = JSON.parse(data); } catch (err) { return; } }
                if (data.channel === "megacloud" || data.type === "watching-log" || data.event) {
                    let color = '#8DFFBF';
                    if (data.event === 'error') color = '#ff4d4d';
                    if (data.event === 'complete') color = '#ffdd95';
                    log(data, color);
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6969)
EOF

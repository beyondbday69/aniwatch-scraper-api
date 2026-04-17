from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import HTMLResponse
import requests
from bs4 import BeautifulSoup
import re
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal

app = FastAPI(title="AniwatchTV Unofficial API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest"
}

BASE_URL = "https://aniwatchtv.to"

@app.get("/tester", response_class=HTMLResponse)
def iframe_tester():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Aniwatch API - Iframe Tester</title>
        <style>
            body { font-family: sans-serif; margin: 20px; background: #1a1a1a; color: white; }
            .container { max-width: 1000px; margin: 0 auto; }
            input { width: 80%; padding: 10px; border-radius: 5px; border: none; }
            button { padding: 10px 20px; border-radius: 5px; border: none; background: #ffdd95; color: black; cursor: pointer; font-weight: bold; }
            .iframe-container { margin-top: 20px; background: black; border: 2px solid #333; height: 600px; position: relative; }
            iframe { width: 100%; height: 100%; border: none; }
            .hint { color: #888; margin-top: 10px; font-size: 0.9em; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Aniwatch Iframe Tester</h1>
            <p>Paste the "link" from /sources/{id} below to test if it loads correctly.</p>
            <input type="text" id="urlInput" placeholder="https://megacloud.blog/embed-2/v3/e-1/...">
            <button onclick="testUrl()">Test URL</button>
            <div class="hint">Note: Some servers (like VidSrc) may have X-Frame-Options that prevent loading in a standard iframe.</div>
            <div class="iframe-container">
                <iframe id="testFrame" allowfullscreen="true" sandbox="allow-scripts allow-same-origin allow-forms"></iframe>
            </div>
        </div>
        <script>
            function testUrl() {
                const url = document.getElementById('urlInput').value;
                if(url) {
                    document.getElementById('testFrame').src = url;
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

def parse_items(html):
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    flw_items = soup.find_all('div', class_=re.compile(r'flw-item'))
    
    for item in flw_items:
        try:
            title_tag = item.find('h3', class_='film-name') or item.find('h2', class_='film-name')
            title = title_tag.text.strip() if title_tag else "Unknown"
            
            url_tag = item.find('a', class_='film-poster-ahref')
            url = url_tag.get('href') if url_tag else ""
            # Extract anime_id from URL like /watch/jujutsu-kaisen-20401 or /jujutsu-kaisen-534
            anime_id_match = re.search(r'-(\d+)$', url.split('?')[0])
            anime_id = anime_id_match.group(1) if anime_id_match else ""
            
            if url and url.startswith('/'):
                url = BASE_URL + url
                
            img_tag = item.find('img', class_='film-poster-img')
            img_url = img_tag.get('data-src') or img_tag.get('src') or "" if img_tag else ""
                
            tick_sub = item.find('div', class_='tick-sub')
            tick_dub = item.find('div', class_='tick-dub')
            tick_eps = item.find('div', class_='tick-eps')
            
            items.append({
                "anime_id": anime_id,
                "title": title,
                "url": url,
                "image": img_url,
                "sub": tick_sub.text.strip() if tick_sub else None,
                "dub": tick_dub.text.strip() if tick_dub else None,
                "episodes": tick_eps.text.strip() if tick_eps else None
            })
        except Exception:
            continue
    return items

@app.get("/")
def read_root():
    return {"message": "Welcome to the AniwatchTV Unofficial API"}

@app.get("/popular")
def get_popular():
    try:
        r = requests.get(f"{BASE_URL}/home", headers=HEADERS, timeout=10)
        r.raise_for_status()
        return {"results": parse_items(r.text)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
def search(q: str = Query(..., min_length=1)):
    try:
        r = requests.get(f"{BASE_URL}/search?keyword={q}", headers=HEADERS, timeout=10)
        r.raise_for_status()
        return {"query": q, "results": parse_items(r.text)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/anime/{anime_id}")
def get_anime_details(anime_id: str):
    try:
        # If anime_id is numeric, we need to resolve it to a slug
        if anime_id.isdigit():
            resolved_slug = ""
            pattern = re.compile(rf"-{anime_id}$")
            
            # Search up to 3 pages to find the slug
            for page in range(1, 4):
                search_url = f"{BASE_URL}/search?keyword={anime_id}&page={page}"
                r_search = requests.get(search_url, headers=HEADERS, timeout=10)
                soup_search = BeautifulSoup(r_search.text, 'html.parser')
                
                for a in soup_search.find_all('a', href=True):
                    href = a['href'].split('?')[0]
                    if pattern.search(href):
                        resolved_slug = href.lstrip('/')
                        break
                if resolved_slug:
                    break
            
            if resolved_slug:
                anime_id = resolved_slug
            else:
                # Fallback: try tooltip AJAX if search fails
                r_tooltip = requests.get(f"{BASE_URL}/ajax/v2/anime/tooltip/{anime_id}", headers=HEADERS, timeout=10)
                if r_tooltip.status_code == 200:
                    t_data = r_tooltip.json()
                    if t_data.get("status"):
                        t_soup = BeautifulSoup(t_data.get("html", ""), "html.parser")
                        t_a = t_soup.find("a", href=True)
                        if t_a:
                            anime_id = t_a["href"].lstrip('/')
        
        r = requests.get(f"{BASE_URL}/{anime_id}", headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        
        title = soup.find('h2', class_='film-name')
        description = soup.find('div', class_='film-description')
        img = soup.find('img', class_='film-poster-img')
        
        # Details
        details = {}
        anisc_info = soup.find('div', class_='anisc-info')
        if anisc_info:
            for item in anisc_info.find_all('div', class_='item'):
                text = item.text.strip()
                if ':' in text:
                    key, val = text.split(':', 1)
                    details[key.strip().lower()] = val.strip()

        # Seasons
        seasons = []
        os_list = soup.find('div', class_='os-list')
        if os_list:
            for a in os_list.find_all('a'):
                s_title = a.find('div', class_='title').text.strip() if a.find('div', class_='title') else ""
                s_url = a.get('href')
                s_id_match = re.search(r'-(\d+)$', s_url.split('?')[0])
                s_id = s_id_match.group(1) if s_id_match else ""
                seasons.append({
                    "title": s_title,
                    "url": BASE_URL + s_url,
                    "anime_id": s_id,
                    "is_active": 'active' in a.get('class', [])
                })

        return {
            "anime_id": anime_id,
            "title": title.text.strip() if title else "Unknown",
            "description": description.text.strip() if description else "",
            "image": img.get('src') if img else "",
            "details": details,
            "seasons": seasons
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/episodes/{anime_id}")
def get_episodes(anime_id: str):
    try:
        # If anime_id is a slug, extract the numeric ID
        if not anime_id.isdigit():
            match = re.search(r'-(\d+)$', anime_id)
            if match:
                anime_id = match.group(1)
        
        r = requests.get(f"{BASE_URL}/ajax/v2/episode/list/{anime_id}", headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        soup = BeautifulSoup(data.get("html", ""), 'html.parser')
        ep_items = soup.find_all('a', class_='ep-item')
        
        episodes = []
        for ep in ep_items:
            episodes.append({
                "ep_id": ep.get('data-id'),
                "number": ep.get('data-number'),
                "title": ep.get('title'),
                "url": BASE_URL + ep.get('href')
            })
        return {"anime_id": anime_id, "episodes": episodes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/servers/{ep_id}")
def get_servers(ep_id: str):
    try:
        r = requests.get(f"{BASE_URL}/ajax/v2/episode/servers?episodeId={ep_id}", headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        soup = BeautifulSoup(data.get("html", ""), 'html.parser')
        server_items = soup.find_all('div', class_='server-item')
        
        servers = []
        for s in server_items:
            servers.append({
                "server_id": s.get('data-id'),
                "name": s.text.strip(),
                "type": s.get('data-type') # sub or dub
            })
        return {"episode_id": ep_id, "servers": servers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sources/{server_id}")
def get_sources(server_id: str):
    try:
        r = requests.get(f"{BASE_URL}/ajax/v2/episode/sources?id={server_id}", headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6969)

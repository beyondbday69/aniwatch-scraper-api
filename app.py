from fastapi import FastAPI, HTTPException, Query, Path
import requests
from bs4 import BeautifulSoup
import re
import base64
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal

app = FastAPI(title="Aniwatch Unofficial API")

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

BASE_URL = "https://aniwatch.co.at"

def parse_items(html):
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    
    # Use fallback class if flw-item isn't exactly matched
    flw_items = soup.find_all('div', class_=re.compile(r'flw-item'))
    
    for item in flw_items:
        try:
            title_tag = item.find('h3', class_='film-name')
            if not title_tag:
                title_tag = item.find('h2', class_='film-name')
            
            title = title_tag.text.strip() if title_tag else "Unknown"
            
            url_tag = item.find('a', class_='film-poster-ahref')
            url = url_tag.get('href') if url_tag else ""
            ep_id = url_tag.get('data-id') if url_tag else ""
            
            if url and url.startswith('/'):
                url = BASE_URL + url
                
            img_tag = item.find('img', class_='film-poster-img')
            img_url = ""
            if img_tag:
                img_url = img_tag.get('data-src') or img_tag.get('src') or ""
                
            # sub/dub/eps counts
            tick_sub = item.find('div', class_='tick-sub')
            tick_dub = item.find('div', class_='tick-dub')
            tick_eps = item.find('div', class_='tick-eps')
            
            sub = tick_sub.text.strip() if tick_sub else None
            dub = tick_dub.text.strip() if tick_dub else None
            eps = tick_eps.text.strip() if tick_eps else None
            
            items.append({
                "ep_id": ep_id,
                "title": title,
                "url": url,
                "image": img_url,
                "sub": sub,
                "dub": dub,
                "episodes": eps
            })
        except Exception:
            continue
    return items

@app.get("/")
def read_root():
    return {"message": "Welcome to the Aniwatch Unofficial API"}

@app.get("/popular")
def get_popular():
    try:
        r = requests.get(f"{BASE_URL}/most-popular-anime/", headers=HEADERS, timeout=10)
        r.raise_for_status()
        items = parse_items(r.text)
        return {"results": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
def search(q: str = Query(..., min_length=1)):
    try:
        r = requests.get(f"{BASE_URL}/?s={q}", headers=HEADERS, timeout=10)
        r.raise_for_status()
        items = parse_items(r.text)
        return {"query": q, "results": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stream/{ep_id}/{type}")
def get_stream(
    ep_id: str = Path(..., description="Episode ID extracted from search or popular endpoints"),
    type: Literal["sub", "dub", "raw"] = Path(..., description="Type of stream (sub or dub)")
):
    try:
        # 1. Fetch Episode Page using WordPress post ID format to automatically resolve the URL
        url = f"{BASE_URL}/?p={ep_id}"
        r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        r.raise_for_status()
        html = r.text
        
        # 2. Extract Nonce
        nonce_match = re.search(r'var hianime_ep_ajax = \{"ajax_url":"[^"]+","episode_nonce":"([^"]+)"\}', html)
        if not nonce_match:
            raise Exception("Could not find episode nonce")
        nonce = nonce_match.group(1)
        
        # 3. Request Servers
        ajax_url = f"{BASE_URL}/wp-admin/admin-ajax.php"
        payload = {
            'action': 'hianime_episode_servers',
            'episode_id': ep_id,
            'nonce': nonce
        }
        res = requests.post(ajax_url, data=payload, headers=HEADERS, timeout=10)
        res_data = res.json()
        
        # 4. Parse servers HTML
        server_html = res_data.get("html", "")
        soup_servers = BeautifulSoup(server_html, "html.parser")
        server_items = soup_servers.find_all('div', class_='server-item')
        
        servers = []
        for s in server_items:
            server_name = s.get('data-server-name') or s.text.strip()
            server_type = s.get('data-type') # sub or dub
            
            data_hash = s.get('data-hash')
            if data_hash:
                try:
                    video_url = base64.b64decode(data_hash).decode('utf-8')
                    if server_type == type:
                        servers.append({
                            "name": server_name,
                            "type": server_type,
                            "url": video_url
                        })
                except:
                    pass
                    
        if not servers:
            raise HTTPException(status_code=404, detail=f"No '{type}' servers found for episode {ep_id}")
        
        return {
            "episode_id": ep_id,
            "type": type,
            "download_link": res_data.get("dl_link"),
            "servers": servers
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6969)

from fastapi import FastAPI, HTTPException, Query, Path
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
        # Some anime IDs might be slugs, but usually they are just numeric.
        # If it's a numeric ID, we can often access it via a generic URL or search.
        # However, aniwatch usually needs the slug. 
        # For simplicity, if anime_id is just digits, we might need to find the slug first or hope for a redirect.
        # Actually, let's try to fetch it directly if it's a slug, or search for it if it's an ID.
        
        # We will assume anime_id provided is the slug or part of the URL containing the ID.
        url = f"{BASE_URL}/{anime_id}" if not anime_id.isdigit() else f"{BASE_URL}/anime-redirect?id={anime_id}"
        # Since I don't know the exact redirect URL, let's assume the user provides the slug like "rezero-season-4-20569"
        
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

import base64
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

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
AJAX_HEADERS = {**HEADERS, "X-Requested-With": "XMLHttpRequest"}

def get_base(provider: str):
    return "https://aniwatch.co.at" if provider == "co" else "https://aniwatchtv.to"

# --- UTILS ---

def get_slug(url):
    if not url: return ""
    return url.split('?')[0].strip('/').replace('watch/', '', 1).replace('http://', '').replace('https://', '').replace('aniwatchtv.to/', '').replace('aniwatch.co.at/', '')

def parse_card(el):
    t = el.find(['h3', 'h2', 'div'], class_=['film-name', 'film-title', 'desi-head-title']) or el.find('a', title=True)
    a = el.find('a', class_=['film-poster', 'film-poster-ahref']) or el.find('a', href=True)
    i = el.find('img')
    ts = el.find('div', class_='tick-sub'); td = el.find('div', class_='tick-dub'); te = el.find('div', class_='tick-eps')
    
    jname = ""
    dynamic_name = el.find(class_='dynamic-name')
    if dynamic_name and dynamic_name.get('data-jname'): jname = dynamic_name.get('data-jname')
        
    type_name = ""; duration = ""; release_date = ""
    for fdi in el.find_all(['span', 'div'], class_=['fdi-item', 'scd-item']):
        if fdi.find(class_=re.compile(r'tick')): continue
        text = fdi.get_text().strip()
        if not text or text in ["HD", "SD"]: continue
        if "m" in text or "h" in text: duration = text
        elif re.search(r'\d{4}', text): release_date = text
        elif not type_name: type_name = text
            
    dt = el.find('div', class_='desi-description')
    desc = dt.get_text().strip() if dt else ""
    
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
        "description": desc
    }

# --- API ENDPOINTS ---

@app.get("/")
def read_root():
    return {
        "message": "Welcome to AniwatchTV Unofficial API (Hybrid Targeting Enabled)",
        "documentation": "/docs",
        "usage": "Append ?provider=co for aniwatch.co.at or ?provider=tv for aniwatchtv.to (default)",
        "endpoints": {
            "home": "/home",
            "search": "/search?q={query}",
            "anime_details": "/anime/{id_or_slug}",
            "episodes": "/episodes/{anime_id}",
            "servers": "/servers/{ep_id}",
            "sources": "/sources/{server_id}",
            "megaplay": "/megaplay/{ep_id}",
            "megaplay_mal": "/megaplay/mal/{mal_id}/{ep_num}",
            "mal_search": "/mal/search?q={query}",
            "genre": "/genre/{name}"
        }
    }

@app.get("/home")
def get_home(provider: str = "tv"):
    try:
        base = get_base(provider)
        url = f"{base}/home" if provider == "tv" else base
        r = requests.get(url, headers=HEADERS)
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
def get_genre(genre_name: str, page: int = 1, provider: str = "tv"):
    try:
        base = get_base(provider)
        r = requests.get(f"{base}/genre/{genre_name}?page={page}", headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')
        return {"genre": genre_name, "provider": provider, "results": [parse_card(i) for i in soup.find_all('div', class_=re.compile(r'flw-item'))]}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
def search_api(q: str = Query(...), provider: str = "tv"):
    try:
        base = get_base(provider)
        url = f"{base}/search?keyword={q}" if provider == "tv" else f"{base}/?s={q}"
        r = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')
        return {"query": q, "provider": provider, "results": [parse_card(i) for i in soup.find_all('div', class_=re.compile(r'flw-item'))]}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/anime/{anime_id}")
def get_anime(anime_id: str, provider: str = "tv"):
    try:
        base = get_base(provider)
        if anime_id.isdigit():
            url = f"{base}/search?keyword={anime_id}" if provider == "tv" else f"{base}/?s={anime_id}"
            s = BeautifulSoup(requests.get(url, headers=HEADERS).text, 'html.parser')
            p = re.compile(rf"-{anime_id}$")
            for a in s.find_all('a', href=True):
                h = a['href'].split('?')[0]
                if p.search(h): anime_id = get_slug(h); break
        
        r = requests.get(f"{base}/{anime_id}", headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')
        details = {}; info = soup.find('div', class_='anisc-info')
        if info:
            for item in info.find_all('div', class_='item'):
                text = item.get_text().strip()
                if ':' in text: k, v = text.split(':', 1); details[k.strip().lower()] = v.strip()
        return {
            "anime_id": anime_id, 
            "provider": provider,
            "title": soup.find('h2', class_='film-name').get_text().strip() if soup.find('h2', class_='film-name') else "Unknown",
            "description": soup.find('div', class_='film-description').get_text().strip() if soup.find('div', class_='film-description') else "",
            "image": soup.find('img', class_='film-poster-img').get('src') if soup.find('img', class_='film-poster-img') else "",
            "details": details,
            "seasons": [{"title": a.find('div', class_='title').get_text().strip(), "anime_id": get_slug(a.get('href'))} for a in soup.select(".os-list a")]
        }
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/episodes/{anime_id}")
def get_episodes(anime_id: str, provider: str = "tv"):
    try:
        base = get_base(provider)
        if provider == "co":
            r = requests.get(f"{base}/{anime_id}", headers=HEADERS)
            m = re.search(r'episode_nonce":"([^"]+)"', r.text)
            nonce = m.group(1) if m else ""
            soup = BeautifulSoup(r.text, "html.parser")
            detail = soup.find(id="ani_detail")
            real_id = detail.get("data-anime-id") if detail else ""
            payload = {"action": "hianime_episode_list", "anime_id": real_id, "nonce": nonce}
            res = requests.post(f"{base}/wp-admin/admin-ajax.php", data=payload, headers=HEADERS).json()
            s = BeautifulSoup(res.get("html", ""), "html.parser")
            return {"provider": provider, "episodes": [{"ep_id": a.get("data-id", ""), "number": a.get("data-number", ""), "title": a.get("title", "")} for a in s.find_all("a", class_="ep-item")]}
            
        if not anime_id.isdigit():
            m = re.search(r'-(\d+)$', anime_id)
            if m: anime_id = m.group(1)
        r = requests.get(f"{base}/ajax/v2/episode/list/{anime_id}", headers=AJAX_HEADERS)
        s = BeautifulSoup(r.json()["html"], 'html.parser')
        return {"provider": provider, "episodes": [{"ep_id": a["data-id"], "number": a["data-number"], "title": a["title"]} for a in s.find_all("a", class_="ep-item")]}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/servers/{ep_id}")
def get_servers(ep_id: str, provider: str = "tv"):
    try:
        base = get_base(provider)
        if provider == "co":
            r = requests.get(f"{base}/?p={ep_id}", headers=HEADERS, allow_redirects=True)
            m = re.search(r'episode_nonce":"([^"]+)"', r.text)
            nonce = m.group(1) if m else ""
            payload = {"action": "hianime_episode_servers", "episode_id": ep_id, "nonce": nonce}
            res = requests.post(f"{base}/wp-admin/admin-ajax.php", data=payload, headers=HEADERS).json()
            s = BeautifulSoup(res.get("html", ""), "html.parser")
            servers = []
            for d in s.find_all("div", class_="server-item"):
                servers.append({"server_id": d.get("data-hash", ""), "name": d.get("data-server-name") or d.get_text().strip(), "type": d.get("data-type")})
            return {"provider": provider, "servers": servers}

        r = requests.get(f"{base}/ajax/v2/episode/servers?episodeId={ep_id}", headers=AJAX_HEADERS)
        s = BeautifulSoup(r.json()["html"], 'html.parser')
        return {"provider": provider, "servers": [{"server_id": d["data-id"], "name": d.get_text().strip(), "type": d["data-type"]} for d in s.find_all("div", class_="server-item")]}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/sources/{server_id}")
def get_sources(server_id: str, provider: str = "tv"):
    try: 
        if provider == "co":
            try:
                link = base64.b64decode(server_id).decode('utf-8')
                return {"provider": provider, "type": "iframe", "link": link}
            except:
                return {"provider": provider, "type": "iframe", "link": ""}
        base = get_base(provider)
        return requests.get(f"{base}/ajax/v2/episode/sources?id={server_id}", headers=AJAX_HEADERS).json()
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/megaplay/{ep_id}")
def get_megaplay(ep_id: str):
    return {"episode_id": ep_id, "sub": f"https://megaplay.buzz/stream/s-2/{ep_id}/sub", "dub": f"https://megaplay.buzz/stream/s-2/{ep_id}/dub", "raw": f"https://megaplay.buzz/stream/s-2/{ep_id}/raw"}

@app.get("/megaplay/mal/{mal_id}/{ep_num}")
def get_megaplay_mal(mal_id: str, ep_num: str):
    return {
        "mal_id": mal_id,
        "episode_number": ep_num,
        "sub": f"https://megaplay.buzz/stream/mal/{mal_id}/{ep_num}/sub",
        "dub": f"https://megaplay.buzz/stream/mal/{mal_id}/{ep_num}/dub",
        "raw": f"https://megaplay.buzz/stream/mal/{mal_id}/{ep_num}/raw"
    }

@app.get("/mal/search")
def search_mal(q: str = Query(...)):
    try:
        r = requests.get(f"https://api.jikan.moe/v4/anime?q={q}", timeout=10)
        r.raise_for_status()
        data = r.json()
        results = []
        for anime in data.get("data", []):
            results.append({
                "mal_id": str(anime.get("mal_id")),
                "title": anime.get("title"),
                "title_english": anime.get("title_english"),
                "image": anime.get("images", {}).get("jpg", {}).get("image_url"),
                "type": anime.get("type"),
                "episodes": anime.get("episodes"),
                "score": anime.get("score"),
                "year": anime.get("year"),
                "synopsis": anime.get("synopsis")
            })
        return {"query": q, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6969)

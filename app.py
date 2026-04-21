import base64
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

def parse_mal_card(anime):
    return {
        "title": anime.get("title") or "Unknown",
        "japanese_title": anime.get("title_japanese") or "",
        "anime_id": str(anime.get("mal_id", "")),
        "image": anime.get("images", {}).get("jpg", {}).get("large_image_url") or anime.get("images", {}).get("jpg", {}).get("image_url") or "",
        "type": anime.get("type") or "",
        "duration": anime.get("duration") or "",
        "release_date": str(anime.get("year") or ""),
        "sub": None,
        "dub": None,
        "episodes": str(anime.get("episodes") or ""),
        "description": anime.get("synopsis") or ""
    }

@app.get("/mal/home")
def get_mal_home():
    try:
        import time
        r1 = requests.get("https://api.jikan.moe/v4/seasons/now?limit=12", timeout=10).json()
        time.sleep(0.35)
        r2 = requests.get("https://api.jikan.moe/v4/top/anime?filter=bypopularity&limit=10", timeout=10).json()
        time.sleep(0.35)
        r3 = requests.get("https://api.jikan.moe/v4/top/anime?filter=airing&limit=10", timeout=10).json()

        latest = [parse_mal_card(a) for a in r1.get("data", [])]
        popular = [parse_mal_card(a) for a in r2.get("data", [])]
        airing = [parse_mal_card(a) for a in r3.get("data", [])]

        return {
            "spotlight": latest[:5],
            "trending": popular[:10],
            "top_airing": airing,
            "most_popular": popular,
            "most_favorite": popular, 
            "latest_completed": popular,
            "latest_episodes": latest,
            "genres": []
        }
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/mal/genres")
def get_mal_genres():
    try:
        r = requests.get("https://api.jikan.moe/v4/genres/anime", timeout=10)
        r.raise_for_status()
        return {"genres": r.json().get("data", [])}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/mal/anime/{mal_id}")
def get_mal_anime(mal_id: str):
    try:
        r = requests.get(f"https://api.jikan.moe/v4/anime/{mal_id}/full", timeout=10)
        r.raise_for_status()
        return {"details": r.json().get("data", {})}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/mal/episodes/{mal_id}")
def get_mal_episodes(mal_id: str, page: int = 1):
    try:
        r = requests.get(f"https://api.jikan.moe/v4/anime/{mal_id}/episodes?page={page}", timeout=10)
        r.raise_for_status()
        data = r.json()
        return {"episodes": data.get("data", []), "pagination": data.get("pagination", {})}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/docv2", response_class=HTMLResponse)
def custom_docs():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AniwatchTV API Tester (v2)</title>
        <style>
            :root { --bg: #0d1117; --card: #161b22; --primary: #58a6ff; --text: #c9d1d9; --border: #30363d; --success: #2ea043; }
            body { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 0; }
            header { background: var(--card); padding: 20px; border-bottom: 1px solid var(--border); text-align: center; }
            h1 { margin: 0; color: var(--primary); }
            .container { max-width: 1000px; margin: 30px auto; padding: 0 20px; }
            .endpoint { background: var(--card); border: 1px solid var(--border); border-radius: 6px; margin-bottom: 20px; overflow: hidden; }
            .ep-header { padding: 15px 20px; background: rgba(255,255,255,0.02); display: flex; align-items: center; cursor: pointer; user-select: none; border-bottom: 1px solid transparent; }
            .ep-header.open { border-bottom-color: var(--border); }
            .method { background: var(--success); color: #fff; padding: 5px 12px; border-radius: 4px; font-weight: bold; font-size: 14px; margin-right: 15px; }
            .path { font-family: monospace; font-size: 16px; font-weight: bold; flex-grow: 1; }
            .desc { color: #8b949e; font-size: 14px; }
            .ep-body { padding: 20px; display: none; }
            .ep-body.open { display: block; }
            .input-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-size: 14px; font-weight: bold; color: #8b949e; }
            input { width: 100%; padding: 10px; background: #0d1117; border: 1px solid var(--border); color: var(--text); border-radius: 6px; font-family: monospace; box-sizing: border-box; }
            input:focus { outline: none; border-color: var(--primary); }
            button { background: var(--primary); color: #000; border: none; padding: 10px 20px; border-radius: 6px; font-weight: bold; cursor: pointer; transition: 0.2s; }
            button:hover { filter: brightness(1.2); }
            pre { background: #0d1117; padding: 15px; border-radius: 6px; border: 1px solid var(--border); overflow-x: auto; font-size: 13px; max-height: 400px; }
            #api-list { display: flex; flex-direction: column; gap: 20px; }
        </style>
    </head>
    <body>
        <header><h1>Aniwatch API Tester (v2)</h1><p style="color:#8b949e">Interactive Swagger-like Documentation</p></header>
        <div class="container" id="api-list"></div>

        <script>
            const endpoints = [
                { method: "GET", path: "/home", desc: "Get trending, spotlights, etc.", inputs: [{name: "provider", default: "tv"}] },
                { method: "GET", path: "/search", desc: "Search anime", inputs: [{name: "q", default: "naruto"}, {name: "provider", default: "tv"}] },
                { method: "GET", path: "/anime/{anime_id}", desc: "Anime details", inputs: [{name: "anime_id", default: "naruto-20", isPath: true}, {name: "provider", default: "tv"}] },
                { method: "GET", path: "/episodes/{anime_id}", desc: "List episodes", inputs: [{name: "anime_id", default: "naruto-20", isPath: true}, {name: "provider", default: "tv"}] },
                { method: "GET", path: "/servers/{ep_id}", desc: "List servers for episode", inputs: [{name: "ep_id", default: "119865", isPath: true}, {name: "provider", default: "tv"}] },
                { method: "GET", path: "/sources/{server_id}", desc: "Get iframe link", inputs: [{name: "server_id", default: "123456", isPath: true}, {name: "provider", default: "tv"}] },
                { method: "GET", path: "/genre/{genre_name}", desc: "Get anime by genre", inputs: [{name: "genre_name", default: "action", isPath: true}, {name: "page", default: "1"}, {name: "provider", default: "tv"}] },
                { method: "GET", path: "/megaplay/{ep_id}", desc: "Direct megaplay utility", inputs: [{name: "ep_id", default: "119865", isPath: true}] },
                { method: "GET", path: "/megaplay/mal/{mal_id}/{ep_num}", desc: "MegaPlay URL generator via MAL ID", inputs: [{name: "mal_id", default: "5114", isPath: true}, {name: "ep_num", default: "1", isPath: true}] },
                { method: "GET", path: "/mal/search", desc: "MAL search API", inputs: [{name: "q", default: "naruto"}] },
                { method: "GET", path: "/mal/home", desc: "MAL top/current season anime", inputs: [] },
                { method: "GET", path: "/mal/genres", desc: "MAL all genres", inputs: [] },
                { method: "GET", path: "/mal/anime/{mal_id}", desc: "MAL anime details", inputs: [{name: "mal_id", default: "20", isPath: true}] },
                { method: "GET", path: "/mal/episodes/{mal_id}", desc: "MAL episodes list", inputs: [{name: "mal_id", default: "20", isPath: true}, {name: "page", default: "1"}] }
            ];

            const container = document.getElementById("api-list");

            endpoints.forEach((ep, idx) => {
                const epDiv = document.createElement("div");
                epDiv.className = "endpoint";
                
                let inputsHtml = "";
                if(ep.inputs) {
                    ep.inputs.forEach(i => {
                        inputsHtml += `<div class="input-group">
                            <label>${i.name} ${i.isPath ? "(Path)" : "(Query)"}</label>
                            <input type="text" id="input-${idx}-${i.name}" value="${i.default || ''}">
                        </div>`;
                    });
                }

                epDiv.innerHTML = `
                    <div class="ep-header" onclick="toggleBody(${idx})">
                        <span class="method">${ep.method}</span>
                        <span class="path">${ep.path}</span>
                        <span class="desc" style="display:inline-block; margin-left:10px;">- ${ep.desc}</span>
                    </div>
                    <div class="ep-body" id="body-${idx}">
                        ${inputsHtml}
                        <button onclick="executeReq(${idx}, '${ep.path}')">Execute</button>
                        <h4 style="margin-top:20px; color:var(--text);">Response:</h4>
                        <pre id="res-${idx}">Waiting for request...</pre>
                    </div>
                `;
                container.appendChild(epDiv);
            });

            function toggleBody(idx) {
                document.getElementById(`body-${idx}`).classList.toggle("open");
                document.querySelectorAll(".ep-header")[idx].classList.toggle("open");
            }

            async function executeReq(idx, pathTemplate) {
                const ep = endpoints[idx];
                let finalPath = pathTemplate;
                const queryParams = [];

                if(ep.inputs) {
                    ep.inputs.forEach(i => {
                        const val = document.getElementById(`input-${idx}-${i.name}`).value;
                        if(i.isPath) {
                            finalPath = finalPath.replace(`{${i.name}}`, encodeURIComponent(val));
                        } else if (val) {
                            queryParams.push(`${i.name}=${encodeURIComponent(val)}`);
                        }
                    });
                }

                let url = finalPath;
                if(queryParams.length > 0) url += "?" + queryParams.join("&");

                const resBox = document.getElementById(`res-${idx}`);
                resBox.innerText = `Fetching ${url} ...`;
                
                try {
                    const req = await fetch(url);
                    const isJson = req.headers.get("content-type")?.includes("json");
                    if(isJson) {
                        const json = await req.json();
                        resBox.innerText = JSON.stringify(json, null, 2);
                    } else {
                        const text = await req.text();
                        resBox.innerText = text;
                    }
                } catch(e) {
                    resBox.innerText = "Error: " + e.message;
                }
            }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6969)

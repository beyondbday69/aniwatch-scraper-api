from fastapi import FastAPI, HTTPException, Query, Path, Request
from fastapi.responses import HTMLResponse
import requests
from bs4 import BeautifulSoup
import re
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal
import json

app = FastAPI(title="AniwatchTV Unofficial API & Website")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
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
        "japanese_title": jname, "anime_id": get_slug(a['href']) if a else "",
        "image": i.get('data-src') or i.get('src') or "" if i else "",
        "type": type_name, "duration": duration, "release_date": release_date,
        "sub": ts.get_text().strip() if ts else None, "dub": td.get_text().strip() if td else None,
        "episodes": te.get_text().strip() if te else None, "description": desc
    }

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
    r = requests.get(f"{BASE_URL}/genre/{genre_name}?page={page}", headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    return {"genre": genre_name, "results": [parse_card(i) for i in soup.find_all('div', class_=re.compile(r'flw-item'))]}

@app.get("/search")
def search_api(q: str = Query(...)):
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
    details = {}; info = soup.find('div', class_='anisc-info')
    if info:
        for item in info.find_all('div', class_='item'):
            text = item.get_text().strip()
            if ':' in text: k, v = text.split(':', 1); details[k.strip().lower()] = v.strip()
    return {
        "anime_id": anime_id, "title": soup.find('h2', class_='film-name').get_text().strip() if soup.find('h2', class_='film-name') else "Unknown",
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

@app.get("/servers/{ep_id}")
def get_servers(ep_id: str):
    r = requests.get(f"{BASE_URL}/ajax/v2/episode/servers?episodeId={ep_id}", headers=AJAX_HEADERS)
    s = BeautifulSoup(r.json()["html"], 'html.parser')
    return {"servers": [{"server_id": d["data-id"], "name": d.get_text().strip(), "type": d["data-type"]} for d in s.find_all("div", class_="server-item")]}

@app.get("/sources/{server_id}")
def get_sources(server_id: str):
    return requests.get(f"{BASE_URL}/ajax/v2/episode/sources?id={server_id}", headers=AJAX_HEADERS).json()

@app.get("/megaplay/{ep_id}")
def get_megaplay(ep_id: str):
    return {"episode_id": ep_id, "sub": f"https://megaplay.buzz/stream/s-2/{ep_id}/sub", "dub": f"https://megaplay.buzz/stream/s-2/{ep_id}/dub", "raw": f"https://megaplay.buzz/stream/s-2/{ep_id}/raw"}

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
    .hero { height: 70vh; position: relative; background: #000; display: flex; align-items: flex-end; padding: 60px 5%; margin-bottom: 40px; }
    .hero-img { position: absolute; top:0; left:0; width:100%; height:100%; object-fit: cover; opacity: 0.4; }
    .hero-content { position: relative; z-index: 10; max-width: 800px; }
    .hero-title { font-size: 48px; color: var(--primary); margin-bottom: 15px; }
    .hero-desc { color: #ccc; margin-bottom: 25px; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.6; font-size: 18px; }
    .btn-main { background: var(--primary); color: black; padding: 12px 30px; border-radius: 5px; text-decoration: none; font-weight: bold; margin-right: 15px; display: inline-block; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; }
    .card { background: var(--card); border-radius: 8px; overflow: hidden; transition: transform 0.2s; text-decoration: none; color: inherit; border: 1px solid #222; display: flex; flex-direction: column; }
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
    .player-area { width: 100%; aspect-ratio: 16/9; background: #000; border-radius: 8px; position: relative; }
    .episodes-card { background: #181818; border-radius: 8px; padding: 20px; height: fit-content; max-height: 80vh; overflow-y: auto; border: 1px solid #333; }
    .ep-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(50px, 1fr)); gap: 8px; }
    .ep-link { background: #2a2a2a; color: white; text-decoration: none; padding: 10px; border-radius: 4px; text-align: center; font-size: 12px; border: 1px solid #444; }
    .ep-link:hover, .ep-link.active { background: var(--primary); color: #000; border-color: var(--primary); }
    .controls { display: flex; gap: 20px; align-items: center; margin: 20px 0; background: #181818; padding: 15px; border-radius: 8px; border: 1px solid #333; flex-wrap: wrap; }
    .toggle-group { display: flex; align-items: center; gap: 10px; }
    .tab-group { display: flex; background: #222; border-radius: 5px; overflow: hidden; }
    .tab { padding: 6px 15px; cursor: pointer; border: none; background: transparent; color: white; font-weight: bold; font-size: 12px; transition: 0.2s; }
    .tab.active { background: var(--primary); color: black; }
    .season-list { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; }
    .season-item { background: #222; color: white; text-decoration: none; padding: 10px 15px; border-radius: 5px; border: 1px solid #444; font-size: 14px; }
    .season-item:hover, .season-item.active { border-color: var(--primary); color: var(--primary); }
    @media (max-width: 900px) { .detail-container, .watch-layout { flex-direction: column; display: block; } .detail-poster { width: 100%; max-width: 300px; } .hero-title { font-size: 32px; } }
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
    d = get_home(); h = d["spotlight"][0] if d["spotlight"] else None
    hero_html = f'<div class="hero"><img src="{h["image"]}" class="hero-img"><div class="hero-content"><h1 class="hero-title">{h["title"]}</h1><p class="hero-desc">{h["description"]}</p><div style="margin-bottom: 30px;"><span class="badge">{h.get("type", "")}</span><span class="badge">{h.get("duration", "")}</span><span class="badge">SUB {h.get("sub", "")}</span><span class="badge" style="background:#fff;">{h.get("release_date", "")}</span></div><a href="/anime-page?id={h["anime_id"]}" class="btn-main">View Details</a><a href="/watch-page?id={h["anime_id"]}" class="btn-main" style="background:#fff; color:black;">Watch Now</a></div></div>' if h else ""
    cards = "".join([f'<a href="/anime-page?id={a["anime_id"]}" class="card"><img src="{a["image"]}" loading="lazy"><div class="card-info"><div class="card-title">{a["title"]}</div><div class="card-meta">{f"<span class=\"badge\">SUB {a['sub']}</span>" if a["sub"] else ""}<span>{a["type"]}</span></div></div></a>' for a in d["latest_episodes"]])
    return f"<!DOCTYPE html><html><head><title>AniwatchTV</title>{SHARED_CSS}</head><body>{HEADER_HTML}{hero_html}<div class=\"container\"><h2>Latest Episodes</h2><div class=\"grid\">{cards}</div></div></body></html>"

@app.get("/anime-page", response_class=HTMLResponse)
def anime_page_ui(id: str):
    a = get_anime(id); e = get_episodes(id)
    eps = "".join([f'<a href="/watch-page?id={id}&ep={x["ep_id"]}" class="ep-link">{x["number"]}</a>' for x in e["episodes"]])
    sns = "".join([f'<a href="/anime-page?id={s["anime_id"]}" class="season-item {"active" if s["anime_id"] == id else ""}">{s["title"]}</a>' for s in a["seasons"]])
    dets = "".join([f'<div class="meta-item"><span class="meta-key">{k.capitalize()}:</span> <span>{v}</span></div>' for k, v in a["details"].items()])
    return f"<!DOCTYPE html><html><head><title>{a['title']}</title>{SHARED_CSS}</head><body>{HEADER_HTML}<div class=\"container\"><div class=\"detail-container\"><div class=\"detail-poster\"><img src=\"{a['image']}\"></div><div class=\"detail-info\"><h1 style=\"color:var(--primary); font-size:42px;\">{a['title']}</h1><p style=\"font-size:18px; line-height:1.6; color:#ccc;\">{a['description']}</p> {'<div class=\"seasons-section\"><h3>Seasons</h3><div class=\"season-list\">' + sns + '</div></div>' if sns else ''} <div style=\"margin: 30px 0; background:#181818; padding:20px; border-radius:8px; border: 1px solid #333;\">{dets}</div><div class=\"episodes-section\"><h2>Episodes</h2><div class=\"ep-grid\">{eps}</div></div></div></div></div></body></html>"

@app.get("/watch-page", response_class=HTMLResponse)
def watch_page_ui(id: str, ep: str = None, type: str = "sub"):
    a = get_anime(id); e = get_episodes(id)
    cur = ep if ep else (e["episodes"][0]["ep_id"] if e["episodes"] else None)
    eps = ""; nxt = ""; fnd = False
    for x in e["episodes"]:
        active = "active" if x["ep_id"] == cur else ""
        eps += f'<a href="/watch-page?id={id}&ep={x["ep_id"]}&type={type}" class="ep-link {active}">{x["number"]}</a>'
        if fnd: nxt = f"/watch-page?id={id}&ep={x['ep_id']}&type={type}"; fnd = False
        if x["ep_id"] == cur: fnd = True
    src = f"https://megaplay.buzz/stream/s-2/{cur}/{type}" if cur else ""
    return f"""<!DOCTYPE html><html><head><title>Watching {a['title']}</title>{SHARED_CSS}</head><body>{HEADER_HTML}<div class="container"><div class="watch-layout"><div class="main-player"><div class="player-area"><iframe src="{src}" id="player" style="width:100%;height:100%;border:none;" allowfullscreen="true" sandbox="allow-scripts allow-same-origin allow-forms"></iframe></div><div class="controls"><div class="toggle-group"><span>Type:</span><div class="tab-group"><button class="tab {"active" if type=="sub" else ""}" onclick="location.href='/watch-page?id={id}&ep={cur}&type=sub'">SUB</button><button class="tab {"active" if type=="dub" else ""}" onclick="location.href='/watch-page?id={id}&ep={cur}&type=dub'">DUB</button></div></div><div class="toggle-group"><span>Auto Next:</span><div class="tab-group" id="atN_tabs"><button class="tab active" onclick="setAN(true, this)">ON</button><button class="tab" onclick="setAN(false, this)">OFF</button></div></div></div><h1 style="color:var(--primary); margin-top:25px;">{a['title']}</h1><p style="color:#aaa;">{a['description'][:500]}...</p></div><div class="episodes-card"><h3 style="margin-top:0; border-bottom:1px solid #333; padding-bottom:10px; color:var(--primary);">Episodes</h3><div class="ep-grid">{eps}</div></div></div></div><script>const nxt_u = "{nxt}"; let atN = true; function setAN(v, el) {{ atN = v; document.querySelectorAll("#atN_tabs .tab").forEach(b => b.classList.remove("active")); el.classList.add("active"); }} window.addEventListener("message", function(e) {{ let d = e.data; if(typeof d === "string") {{ try {{ d = JSON.parse(d); }} catch(x) {{}} }} if(atN && (d.event === "complete" || d.type === "complete") && nxt_u) {{ window.location.href = nxt_u; }} }});</script></body></html>"""

@app.get("/q", response_class=HTMLResponse)
def search_ui_results(q: str):
    d = search_api(q)
    cards = "".join([f'<a href="/anime-page?id={a["anime_id"]}" class="card"><img src="{a["image"]}"><div class="card-info"><div class="card-title">{a["title"]}</div></div></a>' for a in d["results"]])
    return f"<!DOCTYPE html><html><head><title>Search: {q}</title>{SHARED_CSS}</head><body>{HEADER_HTML}<div class=\"container\"><h2>Results for: {q}</h2><div class=\"grid\">{cards}</div></div></body></html>"

@app.get("/", response_class=HTMLResponse)
def read_root():
    return HTMLResponse("<!DOCTYPE html><html><head><title>AniwatchTV</title><style>body { font-family: 'Segoe UI', sans-serif; margin: 0; background: #0f0f0f; color: #eee; display: flex; align-items: center; justify-content: center; height: 100vh; } .box { text-align: center; background: #181818; padding: 50px; border-radius: 12px; border: 1px solid #333; } .btn { display: inline-block; padding: 15px 40px; background: #ffdd95; color: black; border-radius: 8px; font-weight: bold; text-decoration: none; font-size: 20px; }</style></head><body><div class=\"box\"><h1>AniwatchTV</h1><a href=\"/explore\" class=\"btn\">Enter Website</a></div></body></html>")

@app.get("/tester", response_class=HTMLResponse)
def tester_ui():
    return HTMLResponse("<!DOCTYPE html><html><head><title>Tester</title><style>body { font-family: 'Segoe UI', sans-serif; margin: 0; background: #0f0f0f; color: #eee; display: flex; height: 100vh; } .sidebar { width: 350px; background: #181818; border-right: 1px solid #333; } .main { flex: 1; background: #000; } #log { padding: 20px; font-size: 12px; font-family: monospace; overflow-y: auto; height: 70%; }</style></head><body><div class=\"sidebar\"><div style=\"padding:20px;\"><h3>Tester</h3><input id=u style=\"width:100%; padding:8px; background:#222; color:#fff; border:1px solid #444;\"><button onclick=\"f.src=u.value\" style=\"margin-top:10px; width:100%; padding:10px;\">Load</button></div><div id=log>Logs...</div></div><div class=\"main\"><iframe id=f style=\"width:100%;height:100%;border:none;\" allowfullscreen></iframe></div><script>window.addEventListener(\"message\", (e) => {{ const d = document.createElement(\"div\"); d.innerText = JSON.stringify(e.data); document.getElementById(\"log\").prepend(d); }});</script></body></html>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6969)

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
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
    :root { --bg: #0a0a0f; --card: #121218; --primary: #ffdd95; --accent: #ffcc66; --text: #f0f0f0; --text-muted: #9494a5; }
    body { background: var(--bg); color: var(--text); font-family: 'Poppins', sans-serif; margin: 0; scroll-behavior: smooth; }
    header { background: rgba(10, 10, 15, 0.85); backdrop-filter: blur(15px); padding: 15px 5%; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.05); position: sticky; top:0; z-index:2000; transition: 0.3s; }
    .logo { color: var(--primary); font-size: 26px; font-weight: 700; text-decoration: none; letter-spacing: -0.5px; }
    .nav-links a { color: var(--text); text-decoration: none; margin-left: 25px; font-weight: 500; font-size: 15px; opacity: 0.8; transition: 0.2s; }
    .nav-links a:hover { color: var(--primary); opacity: 1; }
    .search-bar { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 30px; padding: 6px 18px; display: flex; align-items: center; transition: 0.3s; }
    .search-bar:focus-within { border-color: var(--primary); box-shadow: 0 0 15px rgba(255,221,149,0.2); }
    .search-bar input { background: transparent; border: none; color: white; padding: 5px; outline: none; width: 220px; font-family: inherit; }
    .container { padding: 40px 5%; }
    
    .hero { height: 80vh; position: relative; background: #000; display: flex; align-items: flex-end; padding: 80px 5%; margin-bottom: 50px; border-radius: 0 0 40px 40px; }
    .hero-img { position: absolute; top:0; left:0; width:100%; height:100%; object-fit: cover; opacity: 0.5; mask-image: linear-gradient(to top, black 20%, transparent 100%); }
    .hero-content { position: relative; z-index: 10; max-width: 850px; animation: fadeInUp 0.8s ease; }
    .hero-title { font-size: 56px; line-height: 1.1; margin-bottom: 20px; font-weight: 700; background: linear-gradient(to bottom, #fff, #ccc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .hero-desc { color: #aaa; margin-bottom: 30px; line-height: 1.7; font-size: 18px; font-weight: 300; }
    .btn-main { background: var(--primary); color: #000; padding: 14px 35px; border-radius: 8px; text-decoration: none; font-weight: 600; margin-right: 15px; transition: 0.3s; display: inline-block; }
    .btn-main:hover { transform: translateY(-3px); box-shadow: 0 10px 20px rgba(255,221,149,0.3); }
    
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 30px; }
    .card { background: var(--card); border-radius: 15px; overflow: hidden; transition: 0.4s; text-decoration: none; color: inherit; border: 1px solid rgba(255,255,255,0.03); position: relative; }
    .card:hover { transform: scale(1.05); border-color: var(--primary); box-shadow: 0 15px 30px rgba(0,0,0,0.4); }
    .card img { width: 100%; aspect-ratio: 2/3; object-fit: cover; transition: 0.4s; }
    .card:hover img { filter: brightness(0.7); }
    .card-info { padding: 15px; }
    .card-title { font-size: 15px; font-weight: 600; margin-bottom: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .badge { background: var(--primary); color: #000; font-size: 11px; padding: 3px 8px; border-radius: 5px; font-weight: 700; margin-right: 5px; }
    
    .detail-container { display: grid; grid-template-columns: 320px 1fr; gap: 60px; animation: fadeIn 1s; }
    .detail-poster img { width: 100%; border-radius: 20px; box-shadow: 0 20px 50px rgba(0,0,0,0.6); }
    .meta-card { background: rgba(255,255,255,0.03); padding: 25px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.05); }
    
    .watch-layout { display: grid; grid-template-columns: 1fr 380px; gap: 40px; }
    .player-container { position: relative; border-radius: 20px; overflow: hidden; background: #000; box-shadow: 0 20px 60px rgba(0,0,0,0.7); }
    .player-area { width: 100%; aspect-ratio: 16/9; }
    .episodes-card { background: #121218; border-radius: 20px; padding: 25px; border: 1px solid rgba(255,255,255,0.05); }
    .ep-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(55px, 1fr)); gap: 10px; margin-top: 15px; }
    .ep-link { background: rgba(255,255,255,0.05); color: #fff; text-decoration: none; padding: 12px; border-radius: 10px; text-align: center; font-size: 14px; font-weight: 600; transition: 0.2s; }
    .ep-link:hover, .ep-link.active { background: var(--primary); color: #000; }
    
    .controls { display: flex; gap: 25px; align-items: center; margin: 30px 0; background: rgba(255,255,255,0.02); padding: 20px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.05); }
    .tab-group { display: flex; background: rgba(0,0,0,0.3); border-radius: 10px; padding: 5px; border: 1px solid rgba(255,255,255,0.1); }
    .tab { padding: 8px 25px; cursor: pointer; border: none; background: transparent; color: white; font-weight: 600; border-radius: 8px; transition: 0.3s; font-size: 13px; }
    .tab.active { background: var(--primary); color: #000; box-shadow: 0 5px 15px rgba(255,221,149,0.3); }

    @keyframes fadeInUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    @media (max-width: 1000px) { .watch-layout, .detail-container { grid-template-columns: 1fr; } .hero-title { font-size: 38px; } }
</style>
"""

HEADER_HTML = """
<header id="navbar">
    <a href="/explore" class="logo">ANIWATCH.</a>
    <div class="search-bar"><form action="/q" method="GET"><input type="text" name="q" placeholder="Search for your favorite anime..."></form></div>
    <nav class="nav-links"><a href="/explore">Explore</a><a href="/tester">Tools</a><a href="/">API</a></nav>
</header>
"""

@app.get("/explore", response_class=HTMLResponse)
def explore_ui():
    d = get_home(); h = d["spotlight"][0] if d["spotlight"] else None
    hero = ""
    if h: hero = f'<div class="hero"><img src="{h["image"]}" class="hero-img"><div class="hero-content"><h1 class="hero-title">{h["title"]}</h1><p class="hero-desc">{h["description"]}</p><div style="margin-bottom:30px;"><span class="badge" style="background:#fff;">{h.get("type","")}</span><span class="badge">{h.get("duration","")}</span><span class="badge">SUB {h.get("sub","")}</span></div><a href="/anime-page?id={h["anime_id"]}" class="btn-main">Get Started</a><a href="/watch-page?id={h["anime_id"]}" class="btn-main" style="background:rgba(255,255,255,0.1); color:#fff; backdrop-filter:blur(10px);">Watch Free</a></div></div>'
    cards = "".join([f'<a href="/anime-page?id={a["anime_id"]}" class="card"><img src="{a["image"]}" loading="lazy"><div class="card-info"><div class="card-title">{a["title"]}</div><div class="card-meta"><span class="badge">{a["type"]}</span><span style="opacity:0.6;font-size:12px;">{a["duration"]}</span></div></div></a>' for a in d["latest_episodes"]])
    return f"<!DOCTYPE html><html><head><title>Home | Aniwatch</title>{SHARED_CSS}</head><body>{HEADER_HTML}{hero}<div class=\"container\"><h2>Trending Releases</h2><div class=\"grid\">{cards}</div></div></body></html>"

@app.get("/anime-page", response_class=HTMLResponse)
def anime_page_ui(id: str):
    a = get_anime(id); e = get_episodes(id)
    eps = "".join([f'<a href="/watch-page?id={id}&ep={x["ep_id"]}" class="ep-link">{x["number"]}</a>' for x in e["episodes"]])
    sns = "".join([f'<a href="/anime-page?id={s["anime_id"]}" class="season-item {"active" if s["anime_id"] == id else ""}">{s["title"]}</a>' for s in a["seasons"]])
    dets = "".join([f'<div style="margin-bottom:12px; font-size:14px;"><span style="color:var(--primary); font-weight:600; width:100px; display:inline-block;">{k.upper()}</span><span style="opacity:0.8;">{v}</span></div>' for k, v in a["details"].items()])
    return f"<!DOCTYPE html><html><head><title>{a['title']}</title>{SHARED_CSS}</head><body>{HEADER_HTML}<div class=\"container\"><div class=\"detail-container\"><div class=\"detail-poster\"><img src=\"{a['image']}\"></div><div class=\"detail-info\"><h1 style=\"font-size:52px; margin-bottom:20px;\">{a['title']}</h1><p style=\"font-size:18px; color:#aaa; line-height:1.7; margin-bottom:40px;\">{a['description']}</p> {'<div style=\"margin-bottom:30px;\"><h3>SEASONS</h3><div style=\"display:flex;gap:10px;flex-wrap:wrap;\">'+sns+'</div></div>' if sns else ''} <div class=\"meta-card\">{dets}</div><div style=\"margin-top:40px;\"><h2>EPISODES</h2><div class=\"ep-grid\">{eps}</div></div></div></div></div></body></html>"

@app.get("/watch-page", response_class=HTMLResponse)
def watch_page_ui(id: str, ep: str = None, type: str = "sub", autoNext: str = "on"):
    a = get_anime(id); e = get_episodes(id)
    cur = ep if ep else (e["episodes"][0]["ep_id"] if e["episodes"] else None)
    eps = ""; nxt = ""; fnd = False
    for x in e["episodes"]:
        active = "active" if x["ep_id"] == cur else ""
        eps += f'<a href="/watch-page?id={id}&ep={x["ep_id"]}&type={type}&autoNext={autoNext}" class="ep-link {active}">{x["number"]}</a>'
        if fnd: nxt = f"/watch-page?id={id}&ep={x['ep_id']}&type={type}&autoNext={autoNext}"; fnd = False
        if x["ep_id"] == cur: fnd = True
    src = f"https://megaplay.buzz/stream/s-2/{cur}/{type}" if cur else ""
    return f"""<!DOCTYPE html><html><head><title>Watching {a['title']}</title>{SHARED_CSS}</head><body>{HEADER_HTML}<div class="container"><div class="watch-layout"><div class="main-player"><div class="player-container"><div class="player-area"><iframe src="{src}" id="player" style="width:100%;height:100%;border:none;" allowfullscreen></iframe></div></div><div class="controls"><div style="display:flex;align-items:center;gap:10px;"><span style="font-size:14px;font-weight:600;">VERSION</span><div class="tab-group"><button class="tab {"active" if type=="sub" else ""}" onclick="location.href='/watch-page?id={id}&ep={cur}&type=sub&autoNext={autoNext}'">SUB</button><button class="tab {"active" if type=="dub" else ""}" onclick="location.href='/watch-page?id={id}&ep={cur}&type=dub&autoNext={autoNext}'">DUB</button></div></div><div style="display:flex;align-items:center;gap:10px;"><span style="font-size:14px;font-weight:600;">AUTONEXT</span><div class="tab-group"><button class="tab {"active" if autoNext=="on" else ""}" onclick="location.href='/watch-page?id={id}&ep={cur}&type={type}&autoNext=on'">ON</button><button class="tab {"active" if autoNext=="off" else ""}" onclick="location.href='/watch-page?id={id}&ep={cur}&type={type}&autoNext=off'">OFF</button></div></div></div><h1 style="color:var(--primary);">{a['title']}</h1><p style="color:#aaa;line-height:1.6;">{a['description'][:500]}...</p></div><div class="episodes-card"><h3 style="margin-top:0;font-size:18px;">Episodes</h3><div class="ep-grid">{eps}</div></div></div></div><script>const u = "{nxt}"; const f = document.getElementById('player'); function up() {{ f.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-forms'); }} window.addEventListener("message", function(e) {{ let d = e.data; if(typeof d === "string") {{ try {{ d = JSON.parse(d); }} catch(x) {{}} }} if("{autoNext}" === "on" && (d.event === "complete" || d.type === "complete") && u) {{ window.location.href = u; }} }}); up();</script></body></html>"""

@app.get("/q", response_class=HTMLResponse)
def search_ui_results(q: str):
    d = search_api(q)
    cards = "".join([f'<a href="/anime-page?id={a["anime_id"]}" class="card"><img src="{a["image"]}"><div class="card-info"><div class="card-title">{a["title"]}</div></div></a>' for a in d["results"]])
    return f"<!DOCTYPE html><html><head><title>Search: {q}</title>{SHARED_CSS}</head><body>{HEADER_HTML}<div class=\"container\"><h2>Results for: {q}</h2><div class=\"grid\">{cards}</div></div></body></html>"

@app.get("/", response_class=HTMLResponse)
def read_root():
    return HTMLResponse("<!DOCTYPE html><html><head><title>Aniwatch</title><style>body { font-family: 'Poppins', sans-serif; margin: 0; background: #050505; color: #eee; display: flex; align-items: center; justify-content: center; height: 100vh; } .box { text-align: center; background: #121218; padding: 80px; border-radius: 30px; border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 30px 100px rgba(0,0,0,0.8); } .btn { display: inline-block; padding: 18px 50px; background: #ffdd95; color: #000; border-radius: 15px; font-weight: 700; text-decoration: none; font-size: 22px; transition: 0.4s; } .btn:hover { background: #fff; transform: scale(1.1); box-shadow: 0 10px 30px rgba(255,255,255,0.2); }</style></head><body><div class=\"box\"><h1 style=\"font-size:50px;color:#ffdd95;margin-bottom:40px;\">ANIWATCH.</h1><a href=\"/explore\" class=\"btn\">Get Started</a></div></body></html>")

@app.get("/tester", response_class=HTMLResponse)
def tester_ui():
    return HTMLResponse("<!DOCTYPE html><html><head><title>Tester</title><style>body { font-family: sans-serif; margin: 0; background: #0a0a0f; color: #eee; display: flex; height: 100vh; } .sidebar { width: 350px; background: #121218; padding: 20px; border-right: 1px solid #333; } .main { flex: 1; }</style></head><body><div class=\"sidebar\"><h3>PostMessage Debugger</h3><input id=u style=\"width:100%;padding:12px;background:#000;color:#fff;border:1px solid #444;border-radius:8px;\"><button onclick=\"f.src=u.value\" style=\"width:100%;padding:12px;margin-top:10px;background:#ffdd95;border:none;border-radius:8px;font-weight:700;\">Load</button><div id=log style=\"margin-top:20px;font-size:12px;font-family:monospace;color:#888;\">Logs...</div></div><div class=\"main\"><iframe id=f style=\"width:100%;height:100%;border:none;\" allowfullscreen></iframe></div><script>window.addEventListener(\"message\", (e) => {{ const d = document.createElement(\"div\"); d.innerText = JSON.stringify(e.data); document.getElementById(\"log\").prepend(d); }});</script></body></html>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6969)

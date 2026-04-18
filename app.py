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
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0">
<style>
    :root { --bg: #0a0a0f; --card: #121218; --primary: #ffdd95; --accent: #ffcc66; --text: #f0f0f0; --text-muted: #9494a5; }
    * { -webkit-tap-highlight-color: transparent; box-sizing: border-box; }
    body { background: var(--bg); color: var(--text); font-family: 'Poppins', sans-serif; margin: 0; scroll-behavior: smooth; overflow-x: hidden; }
    header { background: rgba(10, 10, 15, 0.9); backdrop-filter: blur(15px); padding: 15px 5%; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.05); position: sticky; top:0; z-index:1000; transition: 0.3s; gap: 20px; }
    .logo { color: var(--primary); font-size: 24px; font-weight: 700; text-decoration: none; flex-shrink: 0; }
    .nav-links { display: flex; gap: 20px; }
    .nav-links a { color: var(--text); text-decoration: none; font-weight: 500; font-size: 14px; opacity: 0.8; transition: 0.2s; }
    .nav-links a:hover { color: var(--primary); opacity: 1; }
    .search-bar { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 30px; padding: 6px 15px; display: flex; align-items: center; flex-grow: 1; max-width: 400px; }
    .search-bar input { background: transparent; border: none; color: white; padding: 5px; outline: none; width: 100%; font-family: inherit; font-size: 14px; }
    .container { padding: 30px 5%; }
    .hero { height: 75vh; position: relative; background: #000; display: flex; align-items: flex-end; padding: 60px 5%; margin-bottom: 40px; }
    .hero-img { position: absolute; top:0; left:0; width:100%; height:100%; object-fit: cover; opacity: 0.4; }
    .hero-content { position: relative; z-index: 10; max-width: 800px; animation: fadeInUp 0.8s ease; }
    .hero-title { font-size: clamp(32px, 8vw, 56px); line-height: 1.1; margin-bottom: 15px; font-weight: 700; }
    .hero-desc { color: #aaa; margin-bottom: 25px; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.6; font-size: 16px; }
    .btn-main { background: var(--primary); color: #000; padding: 12px 30px; border-radius: 8px; text-decoration: none; font-weight: 600; margin-right: 10px; display: inline-block; transition: 0.3s; font-size: 14px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 20px; }
    .card { background: var(--card); border-radius: 12px; overflow: hidden; transition: 0.3s; text-decoration: none; color: inherit; border: 1px solid rgba(255,255,255,0.03); }
    .card:hover { transform: translateY(-5px); border-color: var(--primary); }
    .card img { width: 100%; aspect-ratio: 2/3; object-fit: cover; }
    .card-info { padding: 10px; }
    .card-title { font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .badge { background: var(--primary); color: #000; font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 700; margin-right: 5px; }
    .detail-container { display: grid; grid-template-columns: 300px 1fr; gap: 40px; }
    .detail-poster img { width: 100%; border-radius: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.5); }
    .meta-card { background: rgba(255,255,255,0.03); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); }
    .watch-layout { display: grid; grid-template-columns: 1fr 350px; gap: 30px; }
    .player-container { border-radius: 15px; overflow: hidden; background: #000; box-shadow: 0 10px 40px rgba(0,0,0,0.5); }
    .player-area { width: 100%; aspect-ratio: 16/9; }
    .episodes-card { background: #121218; border-radius: 15px; padding: 20px; height: fit-content; max-height: 80vh; overflow-y: auto; border: 1px solid rgba(255,255,255,0.05); }
    .ep-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(50px, 1fr)); gap: 8px; margin-top: 15px; }
    .ep-link { background: rgba(255,255,255,0.05); color: #fff; text-decoration: none; padding: 10px; border-radius: 8px; text-align: center; font-size: 13px; font-weight: 600; }
    .ep-link.active { background: var(--primary); color: #000; }
    .controls { display: flex; gap: 15px; align-items: center; margin: 20px 0; background: rgba(255,255,255,0.02); padding: 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); flex-wrap: wrap; }
    .tab-group { display: flex; background: rgba(0,0,0,0.3); border-radius: 8px; padding: 4px; border: 1px solid rgba(255,255,255,0.1); }
    .tab { padding: 6px 18px; cursor: pointer; border: none; background: transparent; color: white; font-weight: 600; border-radius: 6px; font-size: 12px; }
    .tab.active { background: var(--primary); color: #000; }
    .season-item { background: rgba(255,255,255,0.05); color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 600; border: 1px solid transparent; transition: 0.3s; }
    .season-item:hover { border-color: var(--primary); color: var(--primary); }
    .season-item.active { background: var(--primary); color: #000; box-shadow: 0 5px 15px rgba(255,221,149,0.2); }
    @keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    @media (max-width: 900px) { header { flex-wrap: wrap; padding: 10px 5%; justify-content: center; } .search-bar { order: 3; max-width: 100%; flex-basis: 100%; } .watch-layout, .detail-container { grid-template-columns: 1fr; } .hero { height: 60vh; padding-bottom: 40px; } .hero-title { font-size: 32px; } .hero-desc { -webkit-line-clamp: 2; font-size: 14px; } }
</style>
"""

HEADER_HTML = """
<header>
    <a href="/explore" class="logo">ANIWATCH.</a>
    <div class="search-bar"><form action="/q" method="GET" style="width:100%"><input type="text" name="q" placeholder="Search anime..."></form></div>
    <nav class="nav-links"><a href="/explore">Home</a><a href="/tester">Tools</a></nav>
</header>
"""

@app.get("/explore", response_class=HTMLResponse)
def explore_ui():
    d = get_home(); h = d["spotlight"][0] if d["spotlight"] else None
    hero = f'<div class="hero"><img src="{h["image"]}" class="hero-img"><div class="hero-content"><h1 class="hero-title">{h["title"]}</h1><p class="hero-desc">{h["description"]}</p><div><a href="/anime-page?id={h["anime_id"]}" class="btn-main">Details</a><a href="/watch-page?id={h["anime_id"]}" class="btn-main" style="background:#fff;">Watch Now</a></div></div></div>' if h else ""
    cards = "".join([f'<a href="/anime-page?id={a["anime_id"]}" class="card"><img src="{a["image"]}" loading="lazy"><div class="card-info"><div class="card-title">{a["title"]}</div><div class="card-meta"><span class="badge">{a["type"]}</span><span style="font-size:11px;opacity:0.6;">{a["duration"]}</span></div></div></a>' for a in d["latest_episodes"]])
    return f"<!DOCTYPE html><html><head><title>Home | Aniwatch</title>{SHARED_CSS}</head><body>{HEADER_HTML}{hero}<div class=\"container\"><h2>New Episodes</h2><div class=\"grid\">{cards}</div></div></body></html>"

@app.get("/anime-page", response_class=HTMLResponse)
def anime_page_ui(id: str):
    a = get_anime(id); e = get_episodes(id)
    eps = "".join([f'<a href="/watch-page?id={id}&ep={x["ep_id"]}" class="ep-link">{x["number"]}</a>' for x in e["episodes"]])
    sns = "".join([f'<a href="/anime-page?id={s["anime_id"]}" class="season-item {"active" if s["anime_id"] == id else ""}">{s["title"]}</a>' for s in a["seasons"]])
    dets = "".join([f'<div style="margin-bottom:8px;font-size:13px;"><span style="color:var(--primary);font-weight:600;width:90px;display:inline-block;">{k.upper()}</span><span style="opacity:0.8;">{v}</span></div>' for k, v in a["details"].items()])
    return f"<!DOCTYPE html><html><head><title>{a['title']}</title>{SHARED_CSS}</head><body>{HEADER_HTML}<div class=\"container\"><div class=\"detail-container\"><div class=\"detail-poster\"><img src=\"{a['image']}\"></div><div class=\"detail-info\"><h1 style=\"margin-top:0;\">{a['title']}</h1><p style=\"color:#aaa;line-height:1.7;margin-bottom:30px;\">{a['description']}</p>{'<div style=\"margin-bottom:25px;\"><h3>SEASONS</h3><div style=\"display:flex;gap:10px;flex-wrap:wrap;\">'+sns+'</div></div>' if sns else ''}<div class=\"meta-card\">{dets}</div><div style=\"margin-top:30px;\"><h2>EPISODES</h2><div class=\"ep-grid\">{eps}</div></div></div></div></div></body></html>"

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
    return f"""<!DOCTYPE html><html><head><title>Watching {a['title']}</title>{SHARED_CSS}</head><body>{HEADER_HTML}<div class="container"><div class="watch-layout"><div class="main-player"><div class="player-container"><div class="player-area"><iframe src="{src}" id="player" style="width:100%;height:100%;border:none;" allowfullscreen></iframe></div></div><div class="controls"><div style="display:flex;align-items:center;gap:10px;"><span style="font-size:12px;font-weight:700;">TYPE</span><div class="tab-group"><button class="tab {"active" if type=="sub" else ""}" onclick="location.href='/watch-page?id={id}&ep={cur}&type=sub&autoNext={autoNext}'">SUB</button><button class="tab {"active" if type=="dub" else ""}" onclick="location.href='/watch-page?id={id}&ep={cur}&type=dub&autoNext={autoNext}'">DUB</button></div></div><div style="display:flex;align-items:center;gap:10px;"><span style="font-size:12px;font-weight:700;">NEXT</span><div class="tab-group"><button class="tab {"active" if autoNext=="on" else ""}" onclick="location.href='/watch-page?id={id}&ep={cur}&type={type}&autoNext=on'">ON</button><button class="tab {"active" if autoNext=="off" else ""}" onclick="location.href='/watch-page?id={id}&ep={cur}&type={type}&autoNext=off'">OFF</button></div></div></div><h1>{a['title']}</h1><p style="color:#aaa;">{a['description'][:500]}...</p></div><div class="episodes-card"><h3 style="margin-top:0; border-bottom:1px solid #333; padding-bottom:10px; color:var(--primary);">Episodes</h3><div class="ep-grid">{eps}</div></div></div></div><script>const u_n = "{nxt}"; const f_p = document.getElementById('player'); function up_s() {{ f_p.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-forms'); }} window.addEventListener("message", function(e) {{ let d = e.data; if(typeof d === "string") {{ try {{ d = JSON.parse(d); }} catch(x) {{}} }} if("{autoNext}" === "on" && (d.event === "complete" || d.type === "complete") && u_n) {{ window.location.href = u_n; }} }}); up_s();</script></body></html>"""

@app.get("/q", response_class=HTMLResponse)
def search_ui_results(q: str):
    d = search_api(q)
    cards = "".join([f'<a href="/anime-page?id={a["anime_id"]}" class="card"><img src="{a["image"]}"><div class="card-info"><div class="card-title">{a["title"]}</div></div></a>' for a in d["results"]])
    return f"<!DOCTYPE html><html><head><title>Search: {q}</title>{SHARED_CSS}</head><body>{HEADER_HTML}<div class=\"container\"><h2>Results for: {q}</h2><div class=\"grid\">{cards}</div></div></body></html>"

@app.get("/", response_class=HTMLResponse)
def read_root():
    return HTMLResponse("<!DOCTYPE html><html><head><title>Aniwatch</title><style>body { font-family: 'Poppins', sans-serif; margin: 0; background: #050505; color: #eee; display: flex; align-items: center; justify-content: center; height: 100vh; } .box { text-align: center; background: #121218; padding: 60px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.05); } .btn { display: inline-block; padding: 15px 40px; background: #ffdd95; color: #000; border-radius: 10px; font-weight: 700; text-decoration: none; }</style></head><body><div class=\"box\"><h1>ANIWATCH.</h1><a href=\"/explore\" class=\"btn\">Get Started</a></div></body></html>")

@app.get("/tester", response_class=HTMLResponse)
def tester_ui():
    return HTMLResponse("<!DOCTYPE html><html><head><title>Tester</title><style>body { font-family: sans-serif; margin: 0; background: #0a0a0f; color: #eee; display: flex; height: 100vh; } .sidebar { width: 350px; background: #121218; padding: 20px; } .main { flex: 1; }</style></head><body><div class=\"sidebar\"><h3>PostMessage Debug</h3><input id=u style=\"width:100%;padding:10px;background:#000;color:#fff;border:1px solid #444;\"><button onclick=\"f.src=u.value\" style=\"width:100%;margin-top:10px;padding:10px;background:#ffdd95;\">Go</button><div id=log style=\"margin-top:20px;font-size:10px;color:#888;\">Logs...</div></div><div class=\"main\"><iframe id=f style=\"width:100%;height:100%;border:none;\" allowfullscreen></iframe></div><script>window.addEventListener(\"message\", (e) => {{ const d = document.createElement(\"div\"); d.innerText = JSON.stringify(e.data); document.getElementById(\"log\").prepend(d); }});</script></body></html>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6969)

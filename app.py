from fastapi import FastAPI, HTTPException, Query, Path, Request
from fastapi.responses import HTMLResponse
import requests
from bs4 import BeautifulSoup
import re
from fastapi.middleware.cors import CORSMiddleware

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
    dn = el.find(class_='dynamic-name')
    if dn and dn.get('data-jname'): jname = dn.get('data-jname')
    tn = ""; dur = ""; rd = ""
    for f in el.find_all(['span', 'div'], class_=['fdi-item', 'scd-item']):
        if f.find(class_=re.compile(r'tick')): continue
        txt = f.get_text().strip()
        if not txt or txt in ["HD", "SD"]: continue
        if "m" in txt or "h" in txt: dur = txt
        elif re.search(r'\d{4}', txt): rd = txt
        elif not tn: tn = txt
    dt = el.find('div', class_='desi-description')
    desc = dt.get_text().strip() if dt else ""
    return {
        "title": t.get('title') or t.get_text().strip() if t else "Unknown",
        "japanese_title": jname, "anime_id": get_slug(a['href']) if a else "",
        "image": i.get('data-src') or i.get('src') or "" if i else "",
        "type": tn, "duration": dur, "release_date": rd,
        "sub": ts.get_text().strip() if ts else None, "dub": td.get_text().strip() if td else None,
        "episodes": te.get_text().strip() if te else None, "description": desc
    }

def LAYOUT(title, content, head=""):
    return f"""
    <!DOCTYPE html><html><head><title>{title}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        :root {{ --bg: #0b0b0b; --card: #151515; --primary: #ffdd95; --text: #f0f0f0; --text-muted: #999; }}
        @keyframes fI {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        body {{ background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; margin: 0; animation: fI 0.4s ease-out; overflow-x: hidden; }}
        header {{ background: rgba(18,18,18,0.85); backdrop-filter: blur(15px); padding: 12px 5%; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #222; position: sticky; top:0; z-index:1000; }}
        .logo {{ color: var(--primary); font-size: 24px; font-weight: 800; text-decoration: none; }}
        .nav-links a {{ color: var(--text); text-decoration: none; margin-left: 20px; font-weight: 600; font-size: 14px; opacity: 0.8; }}
        .search-bar {{ background: #1a1a1a; border: 1px solid #333; border-radius: 25px; padding: 5px 15px; display: flex; align-items: center; }}
        .search-bar input {{ background: transparent; border: none; color: white; padding: 5px; outline: none; width: 150px; font-size: 13px; }}
        .container {{ padding: 20px 5%; }}
        .hero {{ height: 60vh; position: relative; background: #000; display: flex; align-items: flex-end; padding: 40px 5%; margin-bottom: 30px; border-bottom: 1px solid #222; overflow: hidden; }}
        .hero-img {{ position: absolute; top:0; left:0; width:100%; height:100%; object-fit: cover; opacity: 0.4; transition: 1.5s ease; }}
        .hero-content {{ position: relative; z-index: 10; max-width: 800px; }}
        .hero-title {{ font-size: 42px; color: var(--primary); margin: 0 0 15px 0; font-weight: 900; }}
        .btn-main {{ background: var(--primary); color: black; padding: 12px 25px; border-radius: 6px; text-decoration: none; font-weight: bold; margin-right: 10px; display: inline-block; transition: 0.3s; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 20px; }}
        .card, .ep-link, .btn-main, .season-item {{ transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1); }}
        .card {{ background: var(--card); border-radius: 10px; overflow: hidden; text-decoration: none; color: inherit; border: 1px solid #222; display: flex; flex-direction: column; position: relative; }}
        .card:hover, .card.v-hover {{ transform: translateY(-8px); border-color: var(--primary); box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
        .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; transition: 0.5s; }}
        .card-info {{ padding: 12px; background: linear-gradient(to top, #111, var(--card)); }}
        .card-title {{ font-size: 14px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .badge {{ background: var(--primary); color: black; font-size: 10px; padding: 3px 6px; border-radius: 4px; font-weight: 800; margin-right: 5px; }}
        .detail-container {{ display: flex; gap: 30px; }}
        .detail-poster {{ width: 250px; flex-shrink: 0; }}
        .detail-poster img {{ width: 100%; border-radius: 10px; border: 1px solid #333; }}
        .meta-key {{ color: var(--primary); font-weight: 800; width: 110px; display: inline-block; }}
        .watch-layout {{ display: grid; grid-template-columns: 1fr 320px; gap: 25px; }}
        .player-area {{ width: 100%; aspect-ratio: 16/9; background: #000; border-radius: 10px; border: 1px solid #222; overflow: hidden; }}
        .episodes-card {{ background: #161616; border-radius: 10px; padding: 20px; height: fit-content; max-height: 80vh; overflow-y: auto; border: 1px solid #222; }}
        .ep-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(50px, 1fr)); gap: 8px; }}
        .ep-link {{ background: #1f1f1f; color: #fff; text-decoration: none; padding: 10px; border-radius: 6px; text-align: center; font-size: 12px; border: 1px solid #333; }}
        .ep-link:hover, .ep-link.active, .ep-link.v-hover {{ background: var(--primary); color: #000; transform: scale(1.05); }}
        .controls {{ display: flex; gap: 15px; align-items: center; margin: 20px 0; background: #161616; padding: 15px; border-radius: 10px; border: 1px solid #222; flex-wrap: wrap; }}
        .tab-group {{ background: #000; padding: 3px; border-radius: 8px; border: 1px solid #333; display: flex; }}
        .tab {{ padding: 6px 12px; cursor: pointer; border: none; background: transparent; color: white; font-weight: bold; font-size: 11px; border-radius: 5px; }}
        .tab.active {{ background: var(--primary); color: black; }}
        .v-cursor {{ position: fixed; width: 20px; height: 20px; background: rgba(255, 221, 149, 0.4); border: 2px solid var(--primary); border-radius: 50%; pointer-events: none; z-index: 9999; display: none; transform: translate(-50%, -50%); box-shadow: 0 0 10px var(--primary); }}
        @media (max-width: 900px) {{ .detail-container, .watch-layout {{ flex-direction: column; display: block; }} .detail-poster {{ width: 100%; max-width: 250px; margin: 0 auto 20px; }} .hero-title {{ font-size: 28px; }} .episodes-card {{ margin-top: 20px; }} }}
    </style>
    {head}
    </head>
    <body>
    <div id="v-cursor" class="v-cursor"></div>
    <header>
        <a href="/explore" class="logo">AniwatchTV</a>
        <div class="search-bar"><form action="/q" method="GET"><input type="text" name="q" placeholder="Search..."></form></div>
        <nav class="nav-links"><a href="/explore">Home</a><a href="/tester">Tester</a></nav>
    </header>
    {content}
    <script>
        const vc = document.getElementById('v-cursor');
        let lastEl = null;
        document.addEventListener('touchstart', e => {{ vc.style.display = 'block'; update(e); }}, {{passive: false}});
        document.addEventListener('touchmove', e => {{ update(e); }}, {{passive: false}});
        document.addEventListener('touchend', () => {{ vc.style.display = 'none'; if(lastEl) lastEl.classList.remove('v-hover'); lastEl = null; }});
        function update(e) {{
            const t = e.touches[0];
            vc.style.left = t.clientX + 'px'; vc.style.top = t.clientY + 'px';
            const el = document.elementFromPoint(t.clientX, t.clientY);
            const target = el?.closest('.card, .ep-link, .btn-main, .season-item, .tab');
            if (target !== lastEl) {{
                if(lastEl) lastEl.classList.remove('v-hover');
                if(target) target.classList.add('v-hover');
                lastEl = target;
            }}
        }}
    </script>
    </body></html>
    """

@app.get("/home")
def get_home():
    r = requests.get(f"{BASE_URL}/home", headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    data = {{"spotlight": [], "trending": [], "latest_episodes": []}}
    for i in soup.select("#slider .swiper-slide"): data["spotlight"].append(parse_card(i))
    for i in soup.select("#trending-home .swiper-slide"): data["trending"].append(parse_card(i))
    for i in soup.find_all('div', class_=re.compile(r'flw-item')): data["latest_episodes"].append(parse_card(i))
    return data

@app.get("/search")
def search_api(q: str):
    r = requests.get(f"{BASE_URL}/search?keyword={q}", headers=HEADERS)
    return {{"results": [parse_card(i) for i in BeautifulSoup(r.text, 'html.parser').find_all('div', class_=re.compile(r'flw-item'))]}}

@app.get("/anime/{{id}}")
def get_anime(id: str):
    r = requests.get(f"{BASE_URL}/{{id}}", headers=HEADERS)
    s = BeautifulSoup(r.text, 'html.parser')
    d = {{}}; info = s.find('div', class_='anisc-info')
    if info:
        for i in info.find_all('div', class_='item'):
            t = i.get_text().strip()
            if ':' in t: k, v = t.split(':', 1); d[k.strip().lower()] = v.strip()
    return {{
        "title": s.find('h2', class_='film-name').get_text().strip(),
        "description": s.find('div', class_='film-description').get_text().strip(),
        "image": s.find('img', class_='film-poster-img').get('src'),
        "details": d, "seasons": [{{ "title": x.find('div', class_='title').get_text().strip(), "anime_id": get_slug(x.get('href')) }} for x in s.select(".os-list a")]
    }}

@app.get("/episodes/{{id}}")
def get_episodes(id: str):
    if not id.isdigit():
        m = re.search(r'-(\d+)$', id)
        if m: id = m.group(1)
    r = requests.get(f"{BASE_URL}/ajax/v2/episode/list/{{id}}", headers=AJAX_HEADERS)
    s = BeautifulSoup(r.json()["html"], 'html.parser')
    return {{"episodes": [{{ "ep_id": a["data-id"], "number": a["data-number"], "title": a["title"] }} for a in s.find_all("a", class_="ep-item")]}}

@app.get("/explore", response_class=HTMLResponse)
def explore_ui():
    d = get_home(); h = d["spotlight"][0] if d["spotlight"] else None
    hero = f'<div class="hero"><img src="{h["image"]}" class="hero-img"><div class="hero-content"><h1 class="hero-title">{h["title"]}</h1><p class="hero-desc">{h["description"]}</p><a href="/anime-page?id={h["anime_id"]}" class="btn-main">Details</a><a href="/watch-page?id={h["anime_id"]}" class="btn-main" style="background:#fff; color:black;">Watch</a></div></div>' if h else ""
    cards = "".join([f'<a href="/anime-page?id={a["anime_id"]}" class="card"><img src="{a["image"]}" loading="lazy"><div class="card-info"><div class="card-title">{a["title"]}</div><div class="card-meta"><span>{a["type"]}</span></div></div></a>' for a in d["latest_episodes"]])
    return LAYOUT("Home", f"{hero}<div class='container'><h2>Latest Episodes</h2><div class='grid'>{cards}</div></div>")

@app.get("/anime-page", response_class=HTMLResponse)
def anime_page_ui(id: str):
    a = get_anime(id); e = get_episodes(id)
    eps = "".join([f'<a href="/watch-page?id={id}&ep={x["ep_id"]}" class="ep-link">{x["number"]}</a>' for x in e["episodes"]])
    sns = "".join([f'<a href="/anime-page?id={s["anime_id"]}" class="season-item {"active" if s["anime_id"] == id else ""}">{s["title"]}</a>' for s in a["seasons"]])
    dets = "".join([f'<div class="meta-item"><span class="meta-key">{k.capitalize()}:</span> <span>{v}</span></div>' for k, v in a["details"].items()])
    return LAYOUT(a["title"], f"<div class='container'><div class='detail-container'><div class='detail-poster'><img src='{a['image']}'></div><div class='detail-info'><h1>{a['title']}</h1><p>{a['description']}</p><h3>Seasons</h3><div class='season-list'>{sns}</div><div style='margin:20px 0;background:#161616;padding:15px;border-radius:8px;'>{dets}</div><h2>Episodes</h2><div class='ep-grid'>{eps}</div></div></div></div>")

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
    src = f"https://megaplay.buzz/stream/s-2/{cur}/{type}"
    cnt = f"""<div class="container"><div class="watch-layout"><div><div class="player-area"><iframe src="{src}" id="player" style="width:100%;height:100%;border:none;" allowfullscreen sandbox="allow-scripts allow-same-origin allow-forms"></iframe></div><div class="controls"><div class="toggle-group"><span>Type:</span><div class="tab-group"><button class="tab {"active" if type=="sub" else ""}" onclick="location.href='/watch-page?id={id}&ep={cur}&type=sub'">SUB</button><button class="tab {"active" if type=="dub" else ""}" onclick="location.href='/watch-page?id={id}&ep={cur}&type=dub'">DUB</button></div></div><div class="toggle-group"><span>Next:</span><div class="tab-group" id="atN_tabs"><button class="tab active" onclick="setAN(true, this)">ON</button><button class="tab" onclick="setAN(false, this)">OFF</button></div></div></div><h1>{a['title']}</h1></div><div class="episodes-card"><h3>Episodes</h3><div class="ep-grid">{eps}</div></div></div></div><script>const nxt_u = "{nxt}"; let atN = true; function setAN(v, el) {{ atN = v; document.querySelectorAll("#atN_tabs .tab").forEach(b => b.classList.remove("active")); el.classList.add("active"); }} window.addEventListener("message", e => {{ let d = e.data; if(typeof d === "string") {{ try {{ d = JSON.parse(d); }} catch(x) {{}} }} if(atN && (d.event === "complete" || d.type === "complete") && nxt_u) location.href = nxt_u; }});</script>"""
    return LAYOUT(f"Watching {a['title']}", cnt)

@app.get("/q", response_class=HTMLResponse)
def search_ui(q: str):
    d = search_api(q)
    cards = "".join([f'<a href="/anime-page?id={a["anime_id"]}" class="card"><img src="{a["image"]}"><div class="card-info"><div class="card-title">{a["title"]}</div></div></a>' for a in d["results"]])
    return LAYOUT(f"Search: {q}", f"<div class='container'><h2>Results for: {q}</h2><div class='grid'>{cards}</div></div>")

@app.get("/", response_class=HTMLResponse)
def root():
    return LAYOUT("AniwatchTV", "<div style='height:80vh;display:flex;align-items:center;justify-content:center;text-align:center;'><div><h1>AniwatchTV</h1><a href='/explore' class='btn-main'>Enter Website</a></div></div>")

@app.get("/tester", response_class=HTMLResponse)
def tester():
    return LAYOUT("Tester", "<div class='container'><h3>Iframe Tester</h3><input id=u style='width:80%;padding:10px;background:#222;color:#fff;border:1px solid #444;'><button onclick='f.src=u.value' style='padding:10px;'>Load</button><iframe id=f style='width:100%;height:600px;margin-top:20px;border:none;' allowfullscreen></iframe></div><script>window.addEventListener('message', e => console.log(e.data));</script>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6969)

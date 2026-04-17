import requests

BASE_URL = "https://aniwatch-scraper-kappa.vercel.app"
print(f"Testing {BASE_URL}...\n")

def test(endpoint):
    url = f"{BASE_URL}{endpoint}"
    try:
        r = requests.get(url, timeout=10)
        print(f"GET {endpoint} -> {r.status_code}")
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        print(f"GET {endpoint} -> ERROR: {e}")
        return None

# 1. Home
h_data = test("/home")
if h_data: print(f"  Trending: {len(h_data.get('trending', []))} | Latest: {len(h_data.get('latest_episodes', []))}")

# 2. Popular
p_data = test("/popular")
if p_data: print(f"  Results: {len(p_data.get('results', []))}")

# 3. Search
s_data = test("/search?q=monster")
if s_data: print(f"  Results: {len(s_data.get('results', []))}")

# 4. Anime Details
a_data = test("/anime/monster-37")
if a_data: print(f"  Title: {a_data.get('title')} | Seasons: {len(a_data.get('seasons', []))}")

# 5. Episodes
e_data = test("/episodes/monster-37")
ep_id = None
if e_data and e_data.get("episodes"):
    ep_id = e_data["episodes"][0]["ep_id"]
    print(f"  Episodes: {len(e_data['episodes'])} | First Ep ID: {ep_id}")

# 6. Servers
server_id = None
if ep_id:
    sv_data = test(f"/servers/{ep_id}")
    if sv_data and sv_data.get("servers"):
        server_id = sv_data["servers"][0]["server_id"]
        print(f"  Servers: {len(sv_data['servers'])} | First Server ID: {server_id}")

# 7. Sources
if server_id:
    src_data = test(f"/sources/{server_id}")
    if src_data: print(f"  Type: {src_data.get('type')} | Link: {src_data.get('link')[:30]}...")


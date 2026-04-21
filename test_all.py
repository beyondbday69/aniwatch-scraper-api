import requests
import sys
import time

BASE_URL = "https://aniwatch-scraper-kappa.vercel.app"

def print_result(name, url, success, details=""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {name.ljust(25)} | {url}")
    if details and not success:
        print(f"  -> {details}")

def test_endpoint(name, path, expected_status=200, check_json=True, keys_to_check=None):
    url = f"{BASE_URL}{path}"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != expected_status:
            print_result(name, url, False, f"Status code {r.status_code} (expected {expected_status})")
            return None
        
        if check_json:
            try:
                data = r.json()
                if keys_to_check:
                    missing = [k for k in keys_to_check if k not in data]
                    if missing:
                        print_result(name, url, False, f"Missing keys: {missing}")
                        return None
                print_result(name, url, True)
                return data
            except ValueError:
                print_result(name, url, False, "Response is not valid JSON")
                return None
        else:
            print_result(name, url, True)
            return r.text
            
    except requests.exceptions.RequestException as e:
        print_result(name, url, False, f"Request failed: {e}")
        return None

print("Starting API Endpoint Tests...\n")

# 1. Root & Docs
test_endpoint("Root", "/", check_json=True, keys_to_check=["endpoints"])
test_endpoint("Doc v2 (UI)", "/docv2", check_json=False)

# 2. Aniwatch Core (Provider: tv)
test_endpoint("Home (TV)", "/home", keys_to_check=["spotlight", "trending", "latest_episodes"])
test_endpoint("Search (TV)", "/search?q=naruto", keys_to_check=["results"])
test_endpoint("Genre (TV)", "/genre/action", keys_to_check=["results"])

# Get dynamic IDs for deep tests
search_res = test_endpoint("Search for deep tests", "/search?q=naruto")
anime_id = None
if search_res and search_res.get("results"):
    anime_id = search_res["results"][0]["anime_id"]

if anime_id:
    test_endpoint("Anime Details (TV)", f"/anime/{anime_id}", keys_to_check=["title", "episodes"])
    eps_data = test_endpoint("Episodes (TV)", f"/episodes/{anime_id}", keys_to_check=["episodes"])
    
    ep_id = None
    if eps_data and eps_data.get("episodes"):
        ep_id = eps_data["episodes"][0]["ep_id"]
        
    if ep_id:
        srv_data = test_endpoint("Servers (TV)", f"/servers/{ep_id}", keys_to_check=["servers"])
        test_endpoint("MegaPlay (TV)", f"/megaplay/{ep_id}", keys_to_check=["sub", "dub"])
        
        srv_id = None
        if srv_data and srv_data.get("servers"):
            srv_id = srv_data["servers"][0]["server_id"]
            
        if srv_id:
            test_endpoint("Sources (TV)", f"/sources/{srv_id}")
else:
    print("⚠️ Skipping TV deep tests (Search failed)")

# 3. Aniwatch Core (Provider: co)
print("\n--- Provider: CO Tests ---")
test_endpoint("Search (CO)", "/search?q=naruto&provider=co", keys_to_check=["results"])
co_search = test_endpoint("Search for CO deep tests", "/search?q=naruto&provider=co")
co_anime_id = None
if co_search and co_search.get("results"):
    co_anime_id = co_search["results"][0]["anime_id"]

if co_anime_id:
    test_endpoint("Anime Details (CO)", f"/anime/{co_anime_id}?provider=co", keys_to_check=["title"])
    co_eps = test_endpoint("Episodes (CO)", f"/episodes/{co_anime_id}?provider=co", keys_to_check=["episodes"])
    
    co_ep_id = None
    if co_eps and co_eps.get("episodes"):
        co_ep_id = co_eps["episodes"][0]["ep_id"]
        
    if co_ep_id:
        co_srv = test_endpoint("Servers (CO)", f"/servers/{co_ep_id}?provider=co", keys_to_check=["servers"])
        
        co_srv_id = None
        if co_srv and co_srv.get("servers"):
            co_srv_id = co_srv["servers"][0]["server_id"]
            
        if co_srv_id:
            test_endpoint("Sources (CO)", f"/sources/{co_srv_id}?provider=co")
else:
    print("⚠️ Skipping CO deep tests (Search failed)")

# 4. MyAnimeList (MAL)
print("\n--- MAL API Tests ---")
test_endpoint("MAL Home", "/mal/home", keys_to_check=["spotlight", "trending", "top_airing"])
test_endpoint("MAL Genres", "/mal/genres", keys_to_check=["genres"])
test_endpoint("MAL Genre ID", "/mal/genre/1", keys_to_check=["results", "pagination"])
test_endpoint("MAL Search", "/mal/search?q=naruto", keys_to_check=["results"])
test_endpoint("MAL Anime Details", "/mal/anime/20", keys_to_check=["details"])
test_endpoint("MAL Episodes", "/mal/episodes/20", keys_to_check=["episodes"])
test_endpoint("MegaPlay MAL", "/megaplay/mal/20/1", keys_to_check=["sub", "dub", "raw"])

print("\nTesting Complete.")

import requests
from bs4 import BeautifulSoup
import re

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
BASE_URL = "https://aniwatch.co.at"

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

def scrape_home_page():
    """Home page scraper — scrape https://aniwatch.co.at/"""
    r = requests.get(BASE_URL, headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    data = {"spotlight": [], "trending": [], "latest_episodes": []}
    for item in soup.select("#slider .swiper-slide"): data["spotlight"].append(parse_card(item))
    for item in soup.select("#trending-home .swiper-slide"): data["trending"].append(parse_card(item))
    for item in soup.find_all('div', class_=re.compile(r'flw-item')): data["latest_episodes"].append(parse_card(item))
    return data

def scrape_genres_a_to_z():
    """Genres A to Z list scraper — scrape the genres section on the home page"""
    r = requests.get(BASE_URL, headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    genres_set = set()
    for a in soup.find_all("a", href=True):
        if "/genre/" in a["href"]: genres_set.add(a.text.strip())
    return sorted(list(genres_set))

def scrape_search(query: str):
    """Search scraper — scrape https://aniwatch.co.at/?s=Overflow"""
    r = requests.get(f"{BASE_URL}/?s={query}", headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    return [parse_card(i) for i in soup.find_all('div', class_=re.compile(r'flw-item'))]

def scrape_watch_page(url_or_slug: str):
    """Watch page scraper — scrape https://aniwatch.co.at/overflow-uncensored-episode-8-english-subbed/"""
    url = url_or_slug if url_or_slug.startswith("http") else f"{BASE_URL}/{url_or_slug}"
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    title_tag = soup.find('h2', class_='film-name')
    title = title_tag.get_text().strip() if title_tag else ""
    
    # Optional: extract iframe or server links
    servers = []
    for d in soup.find_all("div", class_="server-item"):
        servers.append({
            "server_id": d.get("data-hash", ""), 
            "name": d.get("data-server-name") or d.get_text().strip(), 
            "type": d.get("data-type")
        })
        
    return {
        "title": title,
        "url": url,
        "servers": servers
    }

def scrape_genre_page(genre: str):
    """Genre page scraper — scrape https://aniwatch.co.at/genre/action/"""
    r = requests.get(f"{BASE_URL}/genre/{genre}/", headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    return [parse_card(i) for i in soup.find_all('div', class_=re.compile(r'flw-item'))]

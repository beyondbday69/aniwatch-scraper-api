import requests
from bs4 import BeautifulSoup

def inspect():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    # Search page
    r = requests.get('https://aniwatch.co.at/?s=Re%3Azero', headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    print("--- Search Page ---")
    flw_items = soup.find_all('div', class_='flw-item')
    print(f"flw-item found: {len(flw_items)}")
    if flw_items:
        print(flw_items[0].prettify()[:1000])
    
    # Episode page
    r = requests.get('https://aniwatch.co.at/classroom-of-the-elite-4th-season-second-year-first-semester-episode-6-english-sub/', headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    print("\n--- Episode Page ---")
    iframes = soup.find_all('iframe')
    print(f"Iframes found: {len(iframes)}")
    for iframe in iframes:
        print(iframe.get('src'))
    
    # Let's find video servers or players
    servers = soup.find_all('div', class_='server-item')
    print(f"Server items found: {len(servers)}")
    if servers:
        print(servers[0].prettify())

inspect()
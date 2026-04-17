import requests
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get('https://aniwatch.co.at/classroom-of-the-elite-4th-season-second-year-first-semester-episode-6-english-sub/', headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

print("--- player-frame ---")
frame = soup.find('div', class_='player-frame')
if frame:
    print(frame.prettify()[:1000])

print("\n--- player-servers ---")
servers = soup.find('div', class_='player-servers')
if servers:
    print(servers.prettify())

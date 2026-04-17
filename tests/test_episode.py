import requests
from bs4 import BeautifulSoup
import re

headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get('https://aniwatch.co.at/classroom-of-the-elite-4th-season-second-year-first-semester-episode-6-english-sub/', headers=headers)
html = r.text

print("Video related strings:")
for line in html.split('\n'):
    line_lower = line.lower()
    if 'iframe' in line_lower or 'video' in line_lower or 'player' in line_lower or 'embed' in line_lower or 'm3u8' in line_lower:
        if len(line.strip()) < 500:
            print(line.strip())

soup = BeautifulSoup(html, 'html.parser')
scripts = soup.find_all('script')
for s in scripts:
    if s.string and ('m3u8' in s.string or 'iframe' in s.string or 'player' in s.string):
        print(s.string[:200])

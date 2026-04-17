import requests
import re
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get('https://aniwatch.co.at/classroom-of-the-elite-4th-season-second-year-first-semester-episode-6-english-sub/', headers=headers)
html = r.text
soup = BeautifulSoup(html, 'html.parser')

scripts = soup.find_all('script', src=True)
js_links = [s['src'] for s in scripts if 'aniwatch' in s['src']]
print("JS Files:", js_links)

for link in js_links:
    try:
        js = requests.get(link, headers=headers).text
        if 'ajax' in js and 'player' in js:
            print(f"\n--- JS FILE: {link} ---")
            lines = js.split('\n')
            for i, line in enumerate(lines):
                if 'action' in line or 'player' in line or 'ajax' in line:
                    if len(line.strip()) < 200:
                        print(line.strip())
    except Exception as e:
        print(e)

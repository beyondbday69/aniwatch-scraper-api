import requests
from bs4 import BeautifulSoup
import re

headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get('https://aniwatch.co.at/classroom-of-the-elite-4th-season-second-year-first-semester-episode-6-english-sub/', headers=headers)
html = r.text

print("Ajax or Post data:")
for line in html.split('\n'):
    line_lower = line.lower()
    if 'ajax' in line_lower or 'data-post' in line_lower or 'data-id' in line_lower:
        if len(line.strip()) < 500:
            print(line.strip())

soup = BeautifulSoup(html, 'html.parser')
body = soup.find('body')
if body:
    print(f"Body class: {body.get('class')}")

import requests
import re

headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get('https://aniwatch.co.at/classroom-of-the-elite-4th-season-second-year-first-semester-episode-6-english-sub/', headers=headers)
html = r.text

print("Looking for ajax action:")
match = re.search(r'var ajaxData = (\{.*?\});|ajaxData\.[a-zA-Z_]+ = [^;]+;', html, re.DOTALL)
if match:
    print(match.group(0))

script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
for script in script_blocks:
    if 'ajax' in script.lower():
        lines = script.split('\n')
        for i, line in enumerate(lines):
            if 'ajaxData' in line or 'action' in line or '$.ajax' in line:
                print(line.strip())

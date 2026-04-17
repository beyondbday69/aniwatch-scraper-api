import requests
import re
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get('https://aniwatch.co.at/home', headers=headers)
html = r.text
nonce_match = re.search(r'var hianime_ep_ajax = \{"ajax_url":"[^"]+","episode_nonce":"([^"]+)"\}', html)
print("Home page nonce:", nonce_match.group(1) if nonce_match else "Not found")

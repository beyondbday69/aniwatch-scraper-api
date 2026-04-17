import requests
import re
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}
r = requests.get('https://aniwatch.co.at/classroom-of-the-elite-4th-season-second-year-first-semester-episode-6-english-sub/', headers=headers)
html = r.text

nonce_match = re.search(r'var hianime_ep_ajax = \{"ajax_url":"[^"]+","episode_nonce":"([^"]+)"\}', html)
if not nonce_match:
    print("Nonce not found")
    exit()

nonce = nonce_match.group(1)
print("Nonce:", nonce)

# We need the post ID or episode ID
# It looks like: data-id="20250" data-anime-id="18942"
soup = BeautifulSoup(html, 'html.parser')
ani_detail = soup.find(id='ani_detail')
if not ani_detail:
    print("ani_detail not found")
    exit()

ep_id = ani_detail.get('data-id')
print("Episode ID:", ep_id)

ajax_url = 'https://aniwatch.co.at/wp-admin/admin-ajax.php'
payload = {
    'action': 'hianime_episode_servers',
    'episode_id': ep_id,
    'nonce': nonce
}
res = requests.post(ajax_url, data=payload, headers=headers)
print("Servers Response:")
print(res.text[:500])

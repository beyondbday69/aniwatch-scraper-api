import requests
import re
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}
r = requests.get('https://aniwatch.co.at/classroom-of-the-elite-4th-season-second-year-first-semester-episode-6-english-sub/', headers=headers)
html = r.text

nonce_match = re.search(r'var hianime_ep_ajax = \{"ajax_url":"[^"]+","episode_nonce":"([^"]+)"\}', html)
nonce = nonce_match.group(1)

soup = BeautifulSoup(html, 'html.parser')
ep_id = soup.find(id='ani_detail').get('data-id')

ajax_url = 'https://aniwatch.co.at/wp-admin/admin-ajax.php'
payload = {
    'action': 'hianime_episode_servers',
    'episode_id': ep_id,
    'nonce': nonce
}
res = requests.post(ajax_url, data=payload, headers=headers).json()
print("DL Link:", res.get("dl_link"))

soup_servers = BeautifulSoup(res.get("html", ""), "html.parser")
servers = soup_servers.find_all('div', class_='server-item')
print(f"Found {len(servers)} servers")
for server in servers:
    print(f"Data ID: {server.get('data-id')}, Server ID: {server.get('data-server-id')}, Text: {server.text.strip()}")

# The video URL is often returned via another ajax call for the specific server.
# Let's see if there's an action in JS for picking a server.

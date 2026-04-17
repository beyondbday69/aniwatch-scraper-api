import requests
from bs4 import BeautifulSoup

url = "https://aniwatchtv.to/rezero-starting-life-in-another-world-season-4-20569?ref=search"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

print("--- Title & Description ---")
title = soup.find('h2', class_='film-name')
print("Title:", title.text.strip() if title else None)

desc = soup.find('div', class_='film-description')
print("Description:", desc.text.strip() if desc else None)

print("\n--- Details (Type, Studios, Date, etc.) ---")
anisc_info = soup.find('div', class_='anisc-info')
if anisc_info:
    for item in anisc_info.find_all('div', class_='item'):
        print(item.text.strip().replace('\n', ' '))

print("\n--- Seasons ---")
os_list = soup.find('div', class_='os-list')
if os_list:
    for a in os_list.find_all('a'):
        print(f"Season Title: {a.find('div', class_='title').text.strip() if a.find('div', class_='title') else ''} | URL: {a.get('href')} | Active: {'active' in a.get('class', [])}")
else:
    print("No seasons found")


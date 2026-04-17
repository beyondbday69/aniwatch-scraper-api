import requests
from bs4 import BeautifulSoup

def test_popular():
    r = requests.get('https://aniwatch.co.at/most-popular-anime/')
    soup = BeautifulSoup(r.text, 'html.parser')
    items = soup.find_all('article')
    if not items:
        # fallback to finding specific classes
        items = soup.find_all('div', class_='flw-item')
    print("Popular items found:", len(items))
    if items:
        print("First popular item:", items[0].prettify()[:500])

def test_search():
    r = requests.get('https://aniwatch.co.at/?s=Re%3Azero')
    soup = BeautifulSoup(r.text, 'html.parser')
    items = soup.find_all('article')
    print("Search items found:", len(items))
    if items:
        print("First search item:", items[0].prettify()[:500])

def test_episode():
    r = requests.get('https://aniwatch.co.at/classroom-of-the-elite-4th-season-second-year-first-semester-episode-6-english-sub/')
    soup = BeautifulSoup(r.text, 'html.parser')
    iframe = soup.find('iframe')
    print("Iframe src:", iframe['src'] if iframe else "None")
    video_area = soup.find('div', id='video-embed')
    print("Video area:", video_area)

test_popular()
test_search()
test_episode()

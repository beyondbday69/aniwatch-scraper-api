import requests

url = "https://megaplay.buzz/api"
headers = {"User-Agent": "Mozilla/5.0"}
try:
    print(f"GET {url}")
    r = requests.get(url, headers=headers)
    print(f"Status: {r.status_code}")
    print(f"Content: {r.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

embed_id = "yj7JDFVa1pGO" # from previous test
url2 = f"https://megaplay.buzz/api/source/{embed_id}"
try:
    print(f"\nGET {url2}")
    r2 = requests.get(url2, headers=headers)
    print(f"Status: {r2.status_code}")
    print(f"Content: {r2.text[:500]}")
except Exception as e:
    print(f"Error: {e}")


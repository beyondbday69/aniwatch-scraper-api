import requests
from bs4 import BeautifulSoup
import json
import sys

def scrape_aniwatch():
    url = "https://aniwatch.co.at/home"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    print(f"Fetching {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Check if we got blocked by cloudflare
        if "Just a moment..." in response.text or "cloudflare" in response.text.lower():
            print("Warning: Cloudflare or anti-bot protection detected. You might need Playwright/Selenium or a specialized bypassing tool.")
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # This is a generic example that extracts all links from the page
        results = []
        for a_tag in soup.find_all('a', href=True):
            title = a_tag.text.strip()
            link = a_tag['href']
            # Make relative links absolute
            if link.startswith('/'):
                link = f"https://aniwatch.co.at{link}"
                
            if title and link:
                results.append({"title": title, "link": link})
                
        # Remove duplicates while preserving order
        unique_results = []
        seen = set()
        for r in results:
            key = (r['title'], r['link'])
            if key not in seen:
                seen.add(key)
                unique_results.append(r)
                
        print(f"Successfully scraped {len(unique_results)} links.")
        
        output_file = "results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(unique_results, f, indent=4, ensure_ascii=False)
            
        print(f"Results saved to {output_file}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error scraping {url}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    scrape_aniwatch()
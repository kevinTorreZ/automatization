import requests
from bs4 import BeautifulSoup
import sys

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_soup(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def inspect(url):
    print(f"\n--- DEBUG: {url} ---")
    soup = get_soup(url)
    if not soup: return
    
    # Try multiple code selectors
    selectors = [
        'pre', 'code', 'textarea', 
        'div.wp-block-code', 'div.entry-content pre'
    ]
    
    for sel in selectors:
        found = soup.select(sel)
        print(f"Selector '{sel}': Found {len(found)}")
        if found:
            preview = found[0].get_text(strip=True)[:100].replace('\n', ' ')
            print(f"  Sample content: {preview}...")

    # Check for another button?
    buttons = soup.find_all('a', class_=lambda x: x and 'button' in x)
    print(f"Found {len(buttons)} buttons.")
    for b in buttons[:3]:
        print(f"  Button: {b.get_text(strip=True)} -> {b.get('href')}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        inspect(sys.argv[1])
    else:
        inspect("https://scriptpastebins.com/leaf-hub-blox-fruits/")

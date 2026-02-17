import requests
from bs4 import BeautifulSoup
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_soup(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def inspect_homepage():
    url = "https://scriptpastebin.com/"
    soup = get_soup(url)
    if not soup: return

    print("--- DEBUG HOMEPAGE STRUCTURE ---")
    # Print hierarchy of main content
    main = soup.find('main')
    if main:
        print(f"Main tag found. Direct children: {len(main.find_all(recursive=False))}")
        for child in main.find_all(recursive=False):
            print(f"  Tag: {child.name}, Class: {child.get('class')}")
    else:
        print("No <main> tag. Searching for div#content or similar...")
        content = soup.find('div', id='content')
        if content:
             print(f"Div#content found. Children: {len(content.find_all(recursive=False))}")
        else:
             print("Dumping first 500 chars of body:")
             print(soup.body.prettify()[:500])

def inspect_detail(url):
    print(f"\n--- DEBUG DETAIL PAGE: {url} ---")
    soup = get_soup(url)
    if not soup: return
    
    # Look for likely code containers
    pres = soup.find_all('pre')
    codes = soup.find_all('code')
    textareas = soup.find_all('textarea')
    
    print(f"Found {len(pres)} <pre> tags.")
    print(f"Found {len(codes)} <code> tags.")
    print(f"Found {len(textareas)} <textarea> tags.")
    
    # Dump the first few classes of divs to see structure
    divs = soup.find_all('div', class_=True)
    print("Prominent div classes:")
    for d in divs[:5]:
        print(f"  div.{'.'.join(d.get('class'))}")

if __name__ == "__main__":
    inspect_homepage()
    # Test with one known URL from previous run if possible, or grab one from homepage
    # inspect_detail("https://scriptpastebin.com/blox-fruits-script-leaf-hub/") 

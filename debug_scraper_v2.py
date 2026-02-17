import requests
from bs4 import BeautifulSoup

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

def inspect_homepage_deep():
    url = "https://scriptpastebin.com/"
    soup = get_soup(url)
    if not soup: return

    print("--- DEBUG HOMEPAGE DEEP INSPECTION ---")
    article = soup.find('article')
    if article:
        # Find headers (h2, h3) which likely contain links
        headers = article.find_all(['h2', 'h3'])
        print(f"Found {len(headers)} headers (h2/h3) inside main article.")
        for i, h in enumerate(headers[:5]):
            link = h.find('a')
            if link:
                print(f"  [{i}] {h.name}: {link.get_text(strip=True)} -> {link.get('href')}")
            else:
                print(f"  [{i}] {h.name}: {h.get_text(strip=True)} (No link)")
                
        # Also check paragraphs or list items just in case
        print(f"Total links inside article: {len(article.find_all('a'))}")
    else:
        print("No article found (unexpected based on previous run).")

def inspect_detail_page():
    url = "https://scriptpastebin.com/blox-fruits-script-leaf-hub/"
    print(f"\n--- DEBUG DETAIL PAGE: {url} ---")
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
            print(f"  Sample content: {found[0].get_text(strip=True)[:50]}...")

    # Also check if there's a specific "Get Script" button or iframe
    iframes = soup.find_all('iframe')
    print(f"Found {len(iframes)} iframes.")
    
    buttons = soup.find_all('a', class_=lambda x: x and 'button' in x)
    print(f"Found {len(buttons)} buttons/links with 'button' class.")
    for b in buttons[:3]:
        print(f"  Button: {b.get_text(strip=True)} -> {b.get('href')}")

if __name__ == "__main__":
    inspect_homepage_deep()
    inspect_detail_page()

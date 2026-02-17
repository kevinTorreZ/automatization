import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def inspect(url):
    print(f"Inspecting: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(e)
        return

    # Find "Get Script" button
    button = soup.find('a', string=lambda t: t and 'Get Script' in t)
    if not button:
        button = soup.find('a', class_=lambda c: c and 'button' in c and 'wp-block-button__link' in c)
    
    if button:
        print(f"Found button: {button.get_text(strip=True)}")
        parent = button.parent
        print(f"Button Parent tag: {parent.name} class: {parent.get('class')}")
        
        # Look at previous siblings of the button (or its parent)
        # Often the button is in a div, and the title is before that div
        
        current = button
        if current.name == 'a' and current.parent.name == 'div' and 'wp-block-button' in current.parent.get('class', []):
             current = current.parent.parent # Go up to wp-block-buttons or content container
        
        print("--- Preceding Elements ---")
        # Traverse backwards
        prev = current.previous_element
        count = 0
        while prev and count < 10:
            if prev.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div']:
                text = prev.get_text(strip=True)
                if text:
                    print(f"[{prev.name}] {text[:50]}...")
                    count += 1
            prev = prev.previous_element

    else:
        print("Button not found")

inspect("https://scriptpastebin.com/blox-fruits-script-leaf-hub/")

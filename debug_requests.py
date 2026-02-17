import requests
from bs4 import BeautifulSoup

def debug_requests():
    url = "https://scriptpastebins.com/leaf-hub-blox-fruits/" # The URL we found in debug_scraper_v4
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"Fetching {url} with requests...")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for pre
        pres = soup.find_all('pre')
        print(f"Found {len(pres)} pre tags.")
        for i, pre in enumerate(pres):
            print(f"Pre {i}: {pre.get_text(strip=True)[:100]}")
            
        # Check for script section
        script_sec = soup.find(id="script-section")
        if script_sec:
            print("Found #script-section")
            print(script_sec.prettify()[:500])
        else:
            print("Did NOT find #script-section")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_requests()

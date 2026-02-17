import requests
from bs4 import BeautifulSoup
import time
import os
import re
import json
from datetime import datetime
from auto_uploader import BubloxUploader

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

OUTPUT_DIR = "scraped_scripts"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

STATE_FILE = "last_run.json"

# Global automation instances
UPLOADER = None
CATEGORIES = []

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_state(data):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Warning: Could not save state: {e}")

def get_soup(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"    [ERROR] fetching {url}: {e}")
        return None

def save_script(title, code):
    safe_title = re.sub(r'[<>:"/\\|?*]', '', title).strip()
    if len(safe_title) > 100: safe_title = safe_title[:100]
    filepath = os.path.join(OUTPUT_DIR, f"{safe_title}.lua")
    
    # Save to file
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"      [SAVED]: {filepath}")
    except:
        pass
        
    # Upload to Bublox
    if UPLOADER and CATEGORIES:
        found_cat = None
        # Try to match title with available categories
        # Case-insensitive check
        for cat in CATEGORIES:
            if cat.lower() in title.lower():
                found_cat = cat
                break
        
        if found_cat:
            print(f"      [MATCH]: '{title}' matches category '{found_cat}'")
            UPLOADER.upload_script(title, code, found_cat)
        else:
            print(f"      [SKIP]: No matching category found for '{title}'")

def scrape_tertiary(url, title):
    # Only reject if it's the main listing site (without 's')
    # The actual script pages are on scriptpastebins.com (with 's')
    if not url or (url.startswith("https://scriptpastebin.com") and "scriptpastebins.com" not in url): return
    # print(f"    -> Visiting Tertiary: {url}")
    soup = get_soup(url)
    if not soup: return

    code = None
    textareas = soup.find_all('textarea')
    if textareas:
        for ta in textareas:
            c = ta.get_text(strip=True)
            if len(c) > 10: 
                code = c
                break
    if not code:
        pres = soup.find_all('pre')
        if pres: code = pres[0].get_text(strip=True)

    if code:
        save_script(title, code)
    else:
        print("      No code found on tertiary page.")

def scrape_detail(url):
    # print(f"  -> Detail: {url}")
    soup = get_soup(url)
    if not soup: return

    # --- DATE VERIFICATION ---
    today_str = datetime.now().strftime("%Y-%m-%d") # Format depends on site?
    # Usually: <time class="entry-date published" datetime="2024-05-20T...">
    # Or text: "May 20, 2024"
    
    post_date = None
    time_tag = soup.find('time', class_='entry-date')
    if not time_tag:
        time_tag = soup.find('time', class_='published')
    
    if time_tag and time_tag.has_attr('datetime'):
        # Extract YYYY-MM-DD
        dt_str = time_tag['datetime'][:10]
        post_date = dt_str
    
    if post_date:
        if post_date != today_str:
            print(f"    [SKIP DATE]: Script date {post_date} is not today ({today_str}).")
            return
        else:
            print(f"    [DATE OK]: {post_date}")
    else:
        print("    [WARNING]: Could not extract date. Proceeding with caution...")

    target_title = "Unknown Script"
    
    # Logic: Button often in div.wp-block-button -> div.wp-block-buttons
    # We want the text element BEFORE that whole block.
    
    button = soup.find('a', string=lambda t: t and 'Get Script' in t)
    if not button:
        button = soup.find('a', class_=lambda c: c and 'button' in c and 'wp-block-button__link' in c)

    if button:
        # Navigate UP to the container block
        container = button
        # Attempt to find the top-level wrapper of the buttons
        # Usually checking for 'wp-block-buttons' or just 'buttons'
        
        # Traverse up max 3 levels to find the row container
        for _ in range(3):
            if container.parent and ('buttons' in container.parent.get('class', []) or 'entry-content' in container.parent.get('class', [])):
                break
            container = container.parent
        
        # If we hit entry-content, we went too far, go back down to button's direct wrapper?
        # Actually, let's just go to button's parent (div.wp-block-button) and then parent (div.wp-block-buttons)
        
        # Better heuristic: Find the element, look at previous siblings. 
        # If sibling is empty text, skip.
        
        curr = container # This should be the block containing the button
        
        # Scan backwards for meaningful text
        found = False
        limit = 5
        while curr and limit > 0:
            curr = curr.previous_sibling
            if curr and curr.name in ['p', 'div', 'h4', 'h3', 'h2', 'h1', 'strong', 'span']:
                text = curr.get_text(strip=True)
                if text and len(text) > 3 and "Step" not in text:
                    target_title = text
                    found = True
                    break
            limit -= 1
        
        if found:
            print(f"    [TITLE ABOVE]: {target_title}")
        else:
            # Fallback to H1
            h1 = soup.find('h1')
            if h1: 
                target_title = h1.get_text(strip=True)
                print(f"    [FALLBACK H1]: {target_title}")

        target_link = button.get('href')
        scrape_tertiary(target_link, target_title)
    else:
        h1 = soup.find('h1')
        if h1: target_title = h1.get_text(strip=True)
        scrape_tertiary(url, target_title)

def main():
    global UPLOADER, CATEGORIES
    
    # Check Daily Run Limit
    state = load_state()
    last_run_date = state.get("last_successful_run", "")
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    if last_run_date == today_str:
        print(f"[INFO] Script already ran successfully today ({today_str}). Exiting to prevent duplicates.")
        # User requested: "si este en true por ejemplo entonces significa que ya se guardaron los scripts de ese dia y no haga el proceso de nuevo"
        return

    # Initialize Automation
    print("Initializing Bublox Automation...")
    UPLOADER = BubloxUploader(headless=True) # Ensure headless matches updated default
    try:
        UPLOADER.start()
        
        # Get credentials from Env Vars or use fallback (User's current hardcoded)
        email = os.getenv("BUBLOX_EMAIL", "kevintorresloyola@gmail.com")
        password = os.getenv("BUBLOX_PASSWORD", "Kkdvk123")
        
        UPLOADER.login(email, password)
        CATEGORIES = UPLOADER.get_categories()
        print(f"Loaded {len(CATEGORIES)} categories for matching.")
    except Exception as e:
        print(f"Automation init failed: {e}")
        # Continue scraping even if automation failed? Or stop?
        # User implies automation is required. But scraper can run.
        # Let's continue but warn.
        print("Continuing scraper without automation...")
        UPLOADER = None

    try:
        base_url = "https://scriptpastebin.com/"
        print(f"Fetching homepage: {base_url}")
        soup = get_soup(base_url)
        if not soup: return

        article = soup.find('article')
        items = []
        if article:
            headers = article.find_all('h3')
            for h in headers:
                a = h.find('a')
                if a: items.append({'link': a.get('href')})
        else:
            headers = soup.find_all('h3')
            for h in headers:
                a = h.find('a')
                if a: items.append({'link': a.get('href')})

        print(f"Found {len(items)} items. Processing...")
        
        for i, item in enumerate(items):
            print(f"Processing Item {i+1}...")
            scrape_detail(item['link'])
            time.sleep(1)
            
        # If we reached here without major crash, mark as successful for today?
        # Or should we only mark if actually uploaded something?
        # User said: "si ya se guardaron los scripts de ese dia"
        # We assume if the process completes, we are done.
        state["last_successful_run"] = today_str
        save_state(state)
        print(f"[SUCCESS] Process completed for {today_str}. State saved.")
            
    finally:
        if UPLOADER:
            print("Closing automation session...")
            UPLOADER.close()

if __name__ == "__main__":
    main()

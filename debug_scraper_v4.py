from playwright.sync_api import sync_playwright
import time

def debug_scrape():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 1. Go to homepage to get a link
        print("Visiting homepage...")
        page.goto("https://scriptpastebin.com/")
        page.wait_for_load_state("networkidle")
        
        # 2. Get first item link
        # Based on main.py logic: article -> h3 -> a or h3 -> a
        # Let's inspect what we get
        link = page.locator("article h3 a").first.get_attribute("href")
        if not link:
            link = page.locator("h3 a").first.get_attribute("href")
            
        print(f"Found link: {link}")
        
        if link:
            # 3. Visit detail page
            print(f"Visiting detail: {link}")
            page.goto(link)
            page.wait_for_load_state("domcontentloaded")
            
            # 4. Find 'Get Script' button/link
            # main.py logic: button = soup.find('a', string=lambda t: t and 'Get Script' in t)
            # Let's see if we can find it
            
            # Check if there is a 'Get Script' link
            get_script_btn = page.get_by_text("Get Script", exact=False)
            if get_script_btn.count() > 0:
                target_url = get_script_btn.first.get_attribute("href")
                print(f"Found 'Get Script' URL: {target_url}")
                
                if target_url:
                    # 5. Visit tertiary
                    print(f"Visiting Tertiary: {target_url}")
                    page.goto(target_url)
                    page.wait_for_load_state("networkidle")
                    
                    # 6. Dump HTML and specific elements
                    print("Dumping Page Title:", page.title())
                    
                    # Check for textareas
                    textareas = page.locator("textarea").all()
                    print(f"Found {len(textareas)} textareas.")
                    for i, ta in enumerate(textareas):
                        print(f"Textarea {i} Content (First 100 chars): {ta.input_value()[:100]}")
                        
                    # Check for pre
                    pres = page.locator("pre").all()
                    print(f"Found {len(pres)} pre tags.")
                    for i, pre in enumerate(pres):
                        print(f"Pre {i} Content (First 100 chars): {pre.text_content()[:100]}")
                        
                    # Dump full HTML to file
                    with open("debug_tertiary.html", "w", encoding="utf-8") as f:
                        f.write(page.content())
                    print("Saved debug_tertiary.html")
                    
            else:
                print("Could not find 'Get Script' button on detail page.")
                
        browser.close()

if __name__ == "__main__":
    debug_scrape()

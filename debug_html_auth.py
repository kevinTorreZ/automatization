from playwright.sync_api import sync_playwright
import time

def dump_auth_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("Navigating to home...")
        page.goto("https://bublox-3b380.web.app/")
        page.wait_for_load_state("networkidle")
        
        # Login
        if page.is_visible("input[type='email']"):
            print("Logging in...")
            page.fill("input[type='email']", "kevintorresloyola@gmail.com")
            page.fill("input[type='password']", "Kkdvk123")
            page.click("button[type='submit']")
            
            try:
                page.wait_for_selector("text=Crear nuevo Contenido", timeout=15000)
                print("Login successful.")
                page.wait_for_timeout(3000) # Wait for animations
            except:
                print("Login might have failed or dashboard slow.")
        
        # Dump HTML
        with open("page_dump_auth.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print("Saved page_dump_auth.html")
        
        browser.close()

if __name__ == "__main__":
    dump_auth_html()

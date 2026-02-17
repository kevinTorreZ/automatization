from playwright.sync_api import sync_playwright

def dump_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("Navigating to login...")
        page.goto("https://bublox-3b380.web.app/login")
        page.wait_for_load_state("networkidle")
        with open("page_dump_login.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print("Saved page_dump_login.html")
        
        print("Navigating to home...")
        page.goto("https://bublox-3b380.web.app/")
        page.wait_for_load_state("networkidle")
        with open("page_dump_home.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print("Saved page_dump_home.html")
        
        browser.close()

if __name__ == "__main__":
    dump_html()

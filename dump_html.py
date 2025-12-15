from playwright.sync_api import sync_playwright

def dump():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("Navigating...")
        # Use domcontentloaded + fixed wait to avoid networkidle timeouts
        page.goto("https://app.anota.ai/m/JLS7eh7xw", wait_until='domcontentloaded', timeout=60000)
        page.wait_for_timeout(10000)
        
        # Scroll down to ensure lazy loaded items appear
        for i in range(5):
            page.mouse.wheel(0, 500)
            page.wait_for_timeout(500)
            
        print("Saving HTML...")
        with open("page_dump.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        
        browser.close()
        print("Done. Saved to page_dump.html")

if __name__ == "__main__":
    dump()

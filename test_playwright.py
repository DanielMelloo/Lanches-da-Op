from playwright.sync_api import sync_playwright

def test_scrape():
    print("Starting Playwright test...")
    try:
        with sync_playwright() as p:
            print("Launching browser...")
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
            print("Browser launched. Creating page...")
            page = browser.new_page()
            print("Page created. Navigating...")
            page.goto("https://example.com", timeout=30000)
            print("Navigation successful!")
            print("Title:", page.title())
            browser.close()
            print("Test finished successfully.")
    except Exception as e:
        print(f"Playwright Error: {e}")

if __name__ == "__main__":
    test_scrape()

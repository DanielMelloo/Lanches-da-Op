from playwright.sync_api import sync_playwright
import json

def debug():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("Navigating...")
        page.goto("https://app.anota.ai/m/JLS7eh7xw", wait_until='domcontentloaded')
        page.wait_for_timeout(10000)
        
        # Scroll to load
        for _ in range(5):
            page.mouse.wheel(0, 500)
            page.wait_for_timeout(500)

        print("Evaluating JS...")
        result = page.evaluate("""() => {
            const results = { categories: [], items: [] };
            
            // Debug logs
            const debugLog = [];

            // Helper to clean price
            const cleanPrice = (str) => str ? str.replace('R$', '').replace(',', '.').trim() : "0.00";

            // 1. Highlights
            const highlightContainer = document.querySelector('.highlight-items-category');
            if (highlightContainer) {
                const catName = highlightContainer.querySelector('.title')?.innerText?.trim() || "Destaques";
                debugLog.push(`Found highlight cat: ${catName}`);
                
                highlightContainer.querySelectorAll('.item').forEach((itemEl, idx) => {
                    const name = itemEl.querySelector('.name')?.innerText?.trim();
                    const priceRaw = itemEl.querySelector('.current')?.innerText?.trim();
                    debugLog.push(`Highlight Item ${idx}: Name=${name}, PriceRaw=${priceRaw}`);
                    
                    if (name && priceRaw) {
                        results.items.push({ category: catName, name, price: cleanPrice(priceRaw) });
                    }
                });
            } else {
                debugLog.push("No highlight container found");
            }

            // 2. Regular
            document.querySelectorAll('.category-container').forEach((catEl, i) => {
                const catName = catEl.querySelector('.title')?.innerText?.trim() || "Outros";
                debugLog.push(`Regular Cat ${i}: ${catName}`);
                
                catEl.querySelectorAll('.item-card').forEach((itemEl, j) => {
                    const name = itemEl.querySelector('.title')?.innerText?.trim();
                    const priceRaw = itemEl.querySelector('.price-value')?.innerText?.trim();
                    debugLog.push(`  Item ${j}: Name=${name}, PriceRaw=${priceRaw}`);
                    
                    if (name && priceRaw) {
                        results.items.push({ category: catName, name, price: cleanPrice(priceRaw) });
                    }
                });
            });
            
            return { results, debugLog };
        }""")
        
        print("--- DEBUG LOGS ---")
        for log in result['debugLog']:
            print(log)
        print("--- ITEMS FOUND ---")
        print(f"Total Items: {len(result['results']['items'])}")
        print(json.dumps(result['results']['items'][:3], indent=2))
        
        browser.close()

if __name__ == "__main__":
    debug()

from playwright.sync_api import sync_playwright

def scrape_menu(url="https://app.anota.ai/m/JLS7eh7xw"):
    print(f"Starting scrape for {url}...")
    
    with sync_playwright() as p:
        # Launch browser logic
        # Add --no-sandbox for root/docker/EC2 environments
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        page = browser.new_page()
        
        try:
            page.goto(url, wait_until='networkidle', timeout=60000)
            # Wait a bit more for JS rendering
            page.wait_for_timeout(5000)
            
            # Execute JS extraction
            scraped_data = page.evaluate("""() => {
                const data = { categories: [], items: [] };
                
                // Categories to scrape
                const targetCategories = ['Espetos', 'Acompanhamentos'];
                
                // Find all category containers
                const categoryContainers = document.querySelectorAll('.category-container, .category');
                
                const uniqueItems = new Map();
                
                categoryContainers.forEach(container => {
                    const titleEl = container.querySelector('.title');
                    if (!titleEl) return;
                    
                    const title = titleEl.innerText.trim();
                    
                    // Check if this is a target category
                    const isTarget = targetCategories.some(t => title.toLowerCase().includes(t.toLowerCase()));
                    
                    if (isTarget) {
                        data.categories.push(title);
                        
                        // Find items within this category
                        const itemCards = container.querySelectorAll('.item-card, .item-container, .item');
                        
                        itemCards.forEach(el => {
                            // Extract fields
                            let name = el.querySelector('.title')?.innerText;
                            let price = el.querySelector('.price-value')?.innerText || el.querySelector('.price')?.innerText;
                            let desc = el.querySelector('.description')?.innerText || '';
                            let img_src = el.querySelector('img')?.src || '';
                            
                            // Check for default placeholder image
                            if (img_src.includes('item_no_image')) {
                                img_src = '';
                            }
                            
                            // Fallback extraction
                            if (!name || !price) {
                                const lines = el.innerText.split('\\n').filter(l => l.trim());
                                if (!price) price = lines.find(l => l.includes('R$'));
                                if (!name) name = lines.find(l => !l.includes('R$') && l.length > 2);
                            }
                            
                            if (name && price) {
                                const cleanName = name.trim();
                                if (!uniqueItems.has(cleanName)) {
                                    uniqueItems.set(cleanName, {
                                        name: cleanName,
                                        price_raw: price.trim(),
                                        description: desc.trim(),
                                        image_url: img_src,
                                        category: title // Track origin category
                                    });
                                }
                            }
                        });
                    }
                });
                
                data.items = Array.from(uniqueItems.values());
                return data;
            }""")
            
            print(f"Found {len(scraped_data.get('items', []))} potential items.")
            return scraped_data
            
        except Exception as e:
            print(f"Error scraping: {e}")
            return {"categories": [], "items": []}
        finally:
            browser.close()

if __name__ == "__main__":
    import json
    data = scrape_menu()
    with open('scraped_menu.txt', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print("Data saved to scraped_menu.txt")

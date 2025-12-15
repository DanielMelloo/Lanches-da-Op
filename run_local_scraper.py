import os
import time

# Override DB config to point to SSH Tunnel
os.environ['DATABASE_URL'] = 'mysql+pymysql://root:CodeEz4ever@127.0.0.1:3307/lanches_da_op'

from app import create_app, db
from models import Item, Sector, Store
from playwright.sync_api import sync_playwright

def scrape_and_save(store_id, url):
    print(f"Scraping {url} for Store ID {store_id}...")
    
    scraped_data = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # Visual for user
        page = browser.new_page()
        try:
            page.goto(url, wait_until='networkidle', timeout=60000)
            page.wait_for_timeout(5000)
            
            # Scroll
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)

            # Extraction
            scraped_data = page.evaluate("""() => {
                const results = { categories: [], items: [] };
                
                document.querySelectorAll('.category-container').forEach(catEl => {
                    const catName = catEl.querySelector('.category-title')?.innerText?.trim() || "Sem Categoria";
                    if (!results.categories.includes(catName)) results.categories.push(catName);
                    
                    catEl.querySelectorAll('.item-card').forEach(itemEl => {
                        const name = itemEl.querySelector('.item-title')?.innerText?.trim();
                        const price = itemEl.querySelector('.item-price')?.innerText?.trim();
                        const desc = itemEl.querySelector('.item-description')?.innerText?.trim() || "";
                        const img = itemEl.querySelector('img')?.src || "";
                        
                        if (name) {
                            results.items.push({
                                category: catName,
                                name: name,
                                price: price,
                                description: desc,
                                image_url: img
                            });
                        }
                    });
                });
                return results;
            }""")
            print(f"Found {len(scraped_data.get('items', []))} items.")
        except Exception as e:
            print(f"Scrape Error: {e}")
        finally:
            browser.close()

    # Database Insertion
    if scraped_data:
        app = create_app()
        with app.app_context():
            store = db.session.get(Store, store_id)
            if not store:
                print("Store not found!")
                return
            
            # 1. Create Sectors
            sector_map = {}
            for cat_name in scraped_data['categories']:
                sec = Sector.query.filter_by(name=cat_name, subsite_id=store.subsite_id).first()
                if not sec:
                    sec = Sector(name=cat_name, subsite_id=store.subsite_id, active=True)
                    db.session.add(sec)
                    db.session.commit()
                    print(f"Created Sector: {cat_name}")
                sector_map[cat_name] = sec.id
            
            # 2. Create Items
            scan_count = 0
            for item_data in scraped_data['items']:
                # Clean price
                price_str = item_data['price'].replace('R$', '').replace(',', '.').strip()
                try:
                    price_val = float(price_str)
                except:
                    price_val = 0.0

                existing_item = Item.query.filter_by(
                    name=item_data['name'], 
                    store_id=store.id
                ).first()

                if existing_item:
                    existing_item.price = price_val
                    existing_item.description = item_data['description']
                    existing_item.image_url = item_data['image_url']
                    print(f"Updated: {item_data['name']}")
                else:
                    new_item = Item(
                        name=item_data['name'],
                        price=price_val,
                        description=item_data['description'],
                        image_url=item_data['image_url'],
                        store_id=store.id,
                        sector_id=sector_map.get(item_data['category']),
                        active=True
                    )
                    db.session.add(new_item)
                    print(f"Added: {item_data['name']}")
                scan_count += 1
            
            db.session.commit()
            print(f"Done! Processed {scan_count} items.")

if __name__ == "__main__":
    # URL and StoreID can be dynamic, hardcoding for user request
    target_url = "https://app.anota.ai/m/JLS7eh7xw" # Example URL from logs
    target_store_id = 1 # Assuming ID 1
    scrape_and_save(target_store_id, target_url)

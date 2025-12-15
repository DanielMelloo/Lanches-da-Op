import os
import time
import sys
from datetime import datetime
import pytz

# Override DB config to point to SSH Tunnel
os.environ['DB_HOST'] = '127.0.0.1:3307'
os.environ['DB_USER'] = 'root'
os.environ['DB_PASSWORD'] = 'CodeEz4ever'
os.environ['DB_NAME'] = 'lanches_da_op'
os.environ['SKIP_SCHEDULER'] = 'true'

from app import create_app, db
from models import Item, Sector, Store
from playwright.sync_api import sync_playwright

def get_sp_time():
    return datetime.now(pytz.timezone('America/Sao_Paulo'))

def scrape_url(url):
    print(f"   Launch Browser -> {url}")
    scraped_data = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # Visual for user
        page = browser.new_page()
        try:
            page.goto(url, wait_until='networkidle', timeout=60000)
            page.wait_for_timeout(10000)
            
            # Scroll
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)

            # Extraction
            scraped_data = page.evaluate("""() => {
                const results = { categories: [], items: [] };
                
                // Helper to clean price
                const cleanPrice = (str) => str ? str.replace('R$', '').replace(',', '.').trim() : "0.00";

                // 1. Process "Highlights" (Os mais pedidos)
                const highlightContainer = document.querySelector('.highlight-items-category');
                if (highlightContainer) {
                    const catName = highlightContainer.querySelector('.title')?.innerText?.trim() || "Destaques";
                    if (!results.categories.includes(catName)) results.categories.push(catName);
                    
                    highlightContainer.querySelectorAll('.item').forEach(itemEl => {
                        const name = itemEl.querySelector('.name')?.innerText?.trim();
                        const priceRaw = itemEl.querySelector('.current')?.innerText?.trim();
                        // Highlights usually don't show desc on card front, or it's hidden
                        const desc = ""; 
                        const img = itemEl.querySelector('img')?.src || "";
                        
                        if (name && priceRaw) {
                            results.items.push({
                                category: catName,
                                name: name,
                                price: cleanPrice(priceRaw),
                                description: desc,
                                image_url: img
                            });
                        }
                    });
                }

                // 2. Process Regular Categories
                document.querySelectorAll('.category-container').forEach(catEl => {
                    const catName = catEl.querySelector('.title')?.innerText?.trim() || "Outros";
                    if (!results.categories.includes(catName)) results.categories.push(catName);
                    
                    catEl.querySelectorAll('.item-card').forEach(itemEl => {
                        const name = itemEl.querySelector('.title')?.innerText?.trim();
                        const priceRaw = itemEl.querySelector('.price-value')?.innerText?.trim();
                        const desc = itemEl.querySelector('.description')?.innerText?.trim() || "";
                        const img = itemEl.querySelector('img')?.src || "";
                        
                        if (name && priceRaw) {
                            results.items.push({
                                category: catName,
                                name: name,
                                price: cleanPrice(priceRaw),
                                description: desc,
                                image_url: img
                            });
                        }
                    });
                });
                
                return results;
            }""")
            print(f"   Found {len(scraped_data.get('items', []))} items.")
        except Exception as e:
            print(f"   Scrape Error: {e}")
        finally:
            browser.close()
    return scraped_data

def process_store(store_id):
    app = create_app()
    with app.app_context():
        store = db.session.get(Store, store_id)
        if not store: return
        
        print(f"[JOB] Checking Store {store.name} (ID: {store.id})...")
        print(f"   Raw Config: {store.scraper_config} (Type: {type(store.scraper_config)})")
        
        # Mark Running
        store.scraper_status = 'running'
        db.session.commit()
        
        url = store.scraper_config.get('url') if store.scraper_config else None
        if not url:
            print("   No URL configured.")
            store.scraper_status = 'error'
            db.session.commit()
            return

        try:
            data = scrape_url(url)
            
            if not data or not data.get('items'):
                print("   No data found.")
                store.scraper_status = 'completed_empty'
                store.scraper_last_run = get_sp_time()
                db.session.commit()
                return

            # Save to DB
            allowed_categories = ["Espetos", "Acompanhamentos", "Os mais pedidos"] # Added "Os mais pedidos" just in case, but user said "Espetos" and "Acompanhamentos"
            # Actually user was specific: "Espetos" and "Acompanhamentos". Let's stick to that strictly?
            # User said: "puxar apenas 'Espetos' ( da sessão espetos) e 'Acompanhamentos (da sessao de acompanhamentos)"
            # Let's clean the input strings and use a target list
            
            # Filter Logic
            target_cats = ["Espetos", "Acompanhamentos"]
            filtered_items = []
            filtered_categories = set()
            
            for it in data['items']:
                # Simple loose matching
                if any(tc.lower() in it['category'].lower() for tc in target_cats):
                    # Check Image for Placeholder
                    if 'item_no_image' in it.get('image_url', ''):
                        it['image_url'] = "/static/placeholders/default.png"

                    filtered_items.append(it)
                    filtered_categories.add(it['category'])
            
            print(f"   Filtering: Kept {len(filtered_items)}/{len(data['items'])} items from categories: {list(filtered_categories)}")
            
            if not filtered_items:
                 print("   No items matched target categories.")
                 # Decide if we want to proceed? Maybe user renamed categories. 
                 # Let's return to avoid deleting everything if logic is strict
                 store.scraper_status = 'completed_empty'
                 db.session.commit()
                 return

            # 1. Create Sectors (Only for filtered)
            sector_map = {}
            for cat_name in filtered_categories:
                sec = Sector.query.filter_by(name=cat_name, subsite_id=store.subsite_id).first()
                if not sec:
                    sec = Sector(name=cat_name, subsite_id=store.subsite_id, active=True, type='category')
                    db.session.add(sec)
                    db.session.commit()
                sector_map[cat_name] = sec.id
            
            # 2. Create Items
            for item_data in filtered_items:
                price_str = item_data['price'].replace('R$', '').replace(',', '.').strip()
                try:
                    price_val = float(price_str)
                except:
                    price_val = 0.0

                existing = Item.query.filter_by(name=item_data['name'], store_id=store.id).first()
                if existing:
                    existing.price = price_val
                    existing.description = item_data['description']
                    existing.image_url = item_data['image_url']
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
            
            store.scraper_status = 'completed'
            store.scraper_last_run = get_sp_time()
            db.session.commit()
            print("   Success! Database updated.")
            
        except Exception as e:
            print(f"   Fatal Error: {e}")
            store.scraper_status = 'error'
            db.session.commit()

def run_worker():
    print("--- Local Scraper Worker Started ---")
    print("Waiting for jobs from EC2 (via Tunnel :3307)...")
    
    while True:
        try:
            app = create_app()
            with app.app_context():
                # Check for pending jobs
                pending_store = Store.query.filter_by(scraper_status='pending').first()
                if pending_store:
                    # Process outside of this session/context to reuse clean context in process func
                    store_id = pending_store.id
                    print(f"\n[JOB FOUND] Store ID {store_id}")
                else:
                    store_id = None
            
            if store_id:
                process_store(store_id)
            else:
                sys.stdout.write('.')
                sys.stdout.flush()
                time.sleep(5)
                
        except Exception as e:
            print(f"\nConnection Error (Retrying in 10s): {e}")
            time.sleep(10)

if __name__ == "__main__":
    try:
        run_worker()
    except KeyboardInterrupt:
        print("\nWorker stopped.")

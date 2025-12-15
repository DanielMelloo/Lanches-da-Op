import sys
import os
import json

# Add parent directory to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from database import db
from models import Subsite, Store, Item

def sync_menu(store_name="RC Espetaria", scraped_file="scraped_menu.txt"):
    app = create_app()
    with app.app_context():
        # 1. Find Store
        print(f"Searching for store '{store_name}'...")
        # Since Store is unique by name per subsite usually, but names can duplicate across subsites. 
        # Ideally we should know the subsite. Assuming unique name for now or picking first.
        store = Store.query.filter(Store.name.ilike(f"%{store_name}%")).first()
        
        if not store:
            print(f"Store '{store_name}' not found!")
            return
            
        print(f"Found Store: ID {store.id} - {store.name} (Subsite ID: {store.subsite_id})")
        
        # 2. Load Scraped Data
        if not os.path.exists(scraped_file):
            print(f"File {scraped_file} not found.")
            return
            
        with open(scraped_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        items_data = data.get('items', [])
        print(f"Loaded {len(items_data)} items from file.")
        
        # 3. Valid Categories Whitelist (Double check, though scraper already filtered)
        valid_cats = ['Espetos', 'Acompanhamentos']
        
        # 4. Sync Items
        count_updated = 0
        count_created = 0
        count_skipped = 0
        
        for item_data in items_data:
            name = item_data.get('name', '').strip()
            price_str = item_data.get('price_raw', '0').replace('R$', '').replace('.', '').replace(',', '.').strip()
            try:
                price = float(price_str)
            except:
                price = 0.0
                
            category = item_data.get('category', '')
            image_url = item_data.get('image_url', '') or '/static/placeholders/default.png'
            
            # Filter logic matching user request
            if "lanchinho" in name.lower():
                print(f"Skipping excluded item: {name}")
                count_skipped += 1
                continue
                
            # Check existance
            existing_item = Item.query.filter_by(store_id=store.id, name=name).first()
            
            if existing_item:
                # Update
                if existing_item.price != price:
                    print(f"Updating price needed for {name}: {existing_item.price} -> {price}")
                    existing_item.price = price
                
                if not existing_item.active:
                    print(f"Re-activating {name}")
                    existing_item.active = True
                
                # Update image if changed and new one is not default placeholder (unless it was empty)
                # If scraped has an image, use it.
                if image_url and image_url != '/static/placeholders/default.png' and existing_item.image_url != image_url:
                     existing_item.image_url = image_url
                     print(f"Updated image for {name}")
                    
                count_updated += 1
            else:
                # Create
                print(f"Creating new item: {name} - R$ {price}")
                new_item = Item(
                    name=name,
                    price=price,
                    store_id=store.id,
                    active=True,
                    image_url=image_url
                )
                db.session.add(new_item)
                count_created += 1
                
        # 5. Deactivate items NOT in scrape (Only for target categories)
        # Find all active items in this store matching our target categories?
        # Since we don't have categories in DB items easily (unless using Store structure, but here items are flat in store)
        # We should be careful not to deactivate "Bebidas" if we only scraped Espetos.
        # User said: "insere todos ... no banco". Didn't explicitly say "disable others".
        # But previous prompt said "se algo ta no bd e nao no site, desativa".
        # CAUTION: We only scraped "Espetos" and "Acompanhamentos". We should NOT touch other items.
        # But we don't know which items in DB are "Espetos" since `Item` model doesn't have `category` field, unfortunately.
        # `Item` belongs to `Store`. If "RC Espetaria" is a mixed store, we can't distinguish.
        # However, checking the scraped data, usually "Espetos" implies the whole store is Espetaria?
        # Let's skip deactivation logic for now to be safe, unless user explicitly demands it for *these* categories.
        # Given "RC Espetaria", likely most items are Espetos.
        # I will skip auto-deactivation to avoid deleting "Bebidas" which we didn't scrape.
        
        db.session.commit()
        print(f"Sync Complete. Created {count_created}, Updated {count_updated}, Skipped {count_skipped}.")

if __name__ == "__main__":
    sync_menu()

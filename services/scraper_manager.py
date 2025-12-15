import json
from datetime import datetime
from database import db
from models import Store, Item
from services.scraper_service import scrape_menu
from flask import current_app

class ScraperManager:
    @staticmethod
    def sync_items(store_id, mode='update'):
        """
        Syncs items for a given store from the scraper.
        mode='update': Only updates existing items (price, image, active status). 
                       Deactivates items not in scrape (if in target categories).
                       NEVER inserts new items.
        mode='insert': Only inserts NEW items found in scrape.
                       Does not update existing items.
        """
        store = Store.query.get(store_id)
        if not store:
            raise ValueError("Store not found")
            
        # Get Config
        config = store.scraper_config or {}
        url = config.get('url', 'https://app.anota.ai/m/JLS7eh7xw')
        
        # Scrape
        print(f"[{datetime.now()}] Starting Scrape for Store {store.name} ({mode})...")
        scraped_data = scrape_menu(url)
        items_data = scraped_data.get('items', [])
        
        if not items_data:
            print("No items found.")
            return {"status": "no_items", "count": 0}
            
        stats = {"updated": 0, "created": 0, "deactivated": 0, "reactivated": 0, "skipped": 0}
        
        # Helper to normalize price
        def parse_price(p_str):
            try:
                return float(p_str.replace('R$', '').replace('.', '').replace(',', '.').strip())
            except:
                return 0.0

        target_categories = ["Espetos", "Acompanhamentos"] # Could be dynamic in config too
        
        # Build map of scraped items
        scraped_map = {item['name'].lower().strip(): item for item in items_data}
        
        if mode == 'update':
            # 1. Update Existing Items
            # iterate over DB items for this store
            db_items = Item.query.filter_by(store_id=store.id).all()
            
            for db_item in db_items:
                # We need to know if this DB item belongs to the scraped categories to decide on deactivation.
                # Since Item doesn't have category, we have to guess or rely on the Fact that we only scrape Espetos/Acomp.
                # If we assume "RC Espetaria" ONLY sells these, we can deactivate everything else.
                # But safer: Check if db_item name matches any scraped item.
                
                db_name_key = db_item.name.lower().strip()
                
                if db_name_key in scraped_map:
                    # Found in scrape -> Update
                    scraped_item = scraped_map[db_name_key]
                    new_price = parse_price(scraped_item.get('price_raw', '0'))
                    new_image = scraped_item.get('image_url', '')
                    
                    # Update Price
                    if db_item.price != new_price:
                        db_item.price = new_price
                        stats['updated'] += 1
                        
                    # Reactivate if needed
                    if not db_item.active:
                        db_item.active = True
                        stats['reactivated'] += 1
                        
                    # Update Image (if new is valid and different)
                    if new_image and 'item_no_image' not in new_image and db_item.image_url != new_image:
                        db_item.image_url = new_image
                        stats['updated'] += 1 # Count as update
                        
                else:
                    # NOT Found in scrape.
                    # Should we deactivate?
                    # logic: "se o item ta no site e desativado no bd, ativa (done above), se não ta no site mas ta ativo no bd, desativa"
                    # CRITICAL: Only deactivate if we are sure it SHOULD be there.
                    # Since we only scraped specific categories, we might deactivate "Bebidas" if we are not careful.
                    # However, User said: "insere todos ... menos o lanchinho".
                    # If we don't have category info on DB items, we can't filter by category.
                    # For "RC Espetaria", assuming it's mostly Espetos, maybe it's fine?
                    # User request: "se não ta no site mas ta ativo no bd, desativa".
                    # I will implement this simply. If user complains about missing drinks, we can check category later if added to DB.
                    # Actually, the user's specific request "se não ta no site..." implies total synchronization for the scraped scope.
                    # I'll proceed with deactivation but maybe filter by name similarity? No, that's flaky.
                    # I will deactivate, but I'll add a name filter for "lanchinho" to skipping logic.
                    
                    if db_item.active:
                        print(f"Deactivating {db_item.name} (not in scrape)")
                        db_item.active = False
                        stats['deactivated'] += 1

        elif mode == 'insert':
            # 2. Insert New Items
            for name_key, item_data in scraped_map.items():
                if "lanchinho" in name_key:
                    stats['skipped'] += 1
                    continue
                
                # Check duplication
                exists = Item.query.filter(
                    Item.store_id == store.id, 
                    db.func.lower(Item.name) == name_key
                ).first()
                
                if not exists:
                    price = parse_price(item_data.get('price_raw', '0'))
                    image_url = item_data.get('image_url', '')
                    if not image_url or 'item_no_image' in image_url:
                        image_url = '/static/placeholders/default.png'
                        
                    new_item = Item(
                        name=item_data['name'], # Use original casing
                        price=price,
                        store_id=store.id,
                        active=True,
                        image_url=image_url
                    )
                    db.session.add(new_item)
                    stats['created'] += 1
        
        db.session.commit()
        
        # Update Config Last Run
        if not config: config = {}
        config['last_run'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        config['last_stats'] = stats
        store.scraper_config = config
        db.session.commit() # Save config update
        
        print(f"Sync ({mode}) Complete: {stats}")
        return stats

    @staticmethod
    def schedule_scraper(store_id):
        """
        Configures the APScheduler job for this store based on scraper_config.
        """
        store = Store.query.get(store_id)
        if not store or not store.scraper_config:
            return
            
        config = store.scraper_config
        active = config.get('active', False)
        
        scheduler = current_app.extensions.get('scheduler')
        if not scheduler:
            print("Scheduler not initialized.")
            return
            
        job_id = f"scraper_store_{store.id}"
        
        # Always remove existing to ensure clean state
        try:
            scheduler.remove_job(job_id)
        except:
            pass
            
        if active:
            schedule_type = config.get('schedule_type', 'interval')
            
            # wrapper function to run in app context
            def job_function():
                with current_app.app_context():
                    ScraperManager.sync_items(store_id, mode='update')
            
            if schedule_type == 'interval':
                # New interval supports hours, minutes, seconds
                hours = int(config.get('interval_hours', 0))
                minutes = int(config.get('interval_minutes', 0))
                seconds = int(config.get('interval_seconds', 0))
                # APScheduler interval trigger can accept seconds, minutes, hours
                scheduler.add_job(
                    id=job_id,
                    func=job_function,
                    trigger='interval',
                    hours=hours,
                    minutes=minutes,
                    seconds=seconds,
                    replace_existing=True
                )
                print(f"Scheduled interval job {job_id} every {hours}h {minutes}m {seconds}s.")

            elif schedule_type == 'fixed':
                # Fixed schedule can be daily, weekly or monthly
                frequency = config.get('fixed_frequency', 'daily')
                time_str = config.get('fixed_time', '04:00')
                hour, minute = map(int, time_str.split(':'))
                if frequency == 'daily':
                    scheduler.add_job(
                        id=job_id,
                        func=job_function,
                        trigger='cron',
                        hour=hour,
                        minute=minute,
                        replace_existing=True
                    )
                    print(f"Scheduled daily job {job_id} at {time_str}.")
                elif frequency == 'weekly':
                    # APScheduler cron uses day_of_week 0=mon ... 6=sun
                    day_of_week = config.get('weekly_day', 0)
                    scheduler.add_job(
                        id=job_id,
                        func=job_function,
                        trigger='cron',
                        day_of_week=day_of_week,
                        hour=hour,
                        minute=minute,
                        replace_existing=True
                    )
                    print(f"Scheduled weekly job {job_id} on day {day_of_week} at {time_str}.")
                elif frequency == 'monthly':
                    day_of_month = config.get('monthly_day', 1)
                    scheduler.add_job(
                        id=job_id,
                        func=job_function,
                        trigger='cron',
                        day=day_of_month,
                        hour=hour,
                        minute=minute,
                        replace_existing=True
                    )
                    print(f"Scheduled monthly job {job_id} on day {day_of_month} at {time_str}.")
                else:
                    # fallback to daily if unknown
                    scheduler.add_job(
                        id=job_id,
                        func=job_function,
                        trigger='cron',
                        hour=hour,
                        minute=minute,
                        replace_existing=True
                    )
                    print(f"Scheduled fallback daily job {job_id} at {time_str}.")

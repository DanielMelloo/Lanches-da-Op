from sqlalchemy import create_engine, text

# Tunnel config
uri = 'mysql+pymysql://root:CodeEz4ever@127.0.0.1:3307/lanches_da_op'

def check():
    engine = create_engine(uri)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT name, image_url FROM items WHERE image_url LIKE '%static/placeholders%' LIMIT 5"))
        rows = res.fetchall()
        print(f"Items with placeholder: {len(rows)}")
        for row in rows:
            print(f" - {row[0]}: {row[1]}")

        # Check for any remaining empty or no_image ones
        res2 = conn.execute(text("SELECT items.name, sectors.name FROM items JOIN sectors ON items.sector_id = sectors.id WHERE items.image_url LIKE '%item_no_image%'"))
        rows2 = res2.fetchall()
        print(f"Items with original 'no_image' url: {len(rows2)}")
        for r in rows2:
            print(f" [Legacy?] {r[0]} ({r[1]})")

if __name__ == "__main__":
    check()

import pymysql

def debug_templates():
    host = '127.0.0.1'
    port = 3307
    user = 'root'
    password = 'CodeEz4ever'
    db_name = 'lanches_da_op'
    
    print(f"Connecting to {host}:{port}/{db_name}...")
    
    try:
        conn = pymysql.connect(
            host=host, port=port, user=user, password=password, database=db_name,
            cursorclass=pymysql.cursors.DictCursor
        )
        with conn.cursor() as cursor:
            # Check if table exists
            cursor.execute("SHOW TABLES LIKE 'whatsapp_template_presets'")
            if not cursor.fetchone():
                print("ERROR: Table 'whatsapp_template_presets' DOES NOT EXIST!")
                return

            # List Subsites
            print("\n--- Subsites ---")
            cursor.execute("SELECT id, name FROM subsites")
            for r in cursor.fetchall():
                print(r)

            # List Presets
            print("\n--- Presets ---")
            cursor.execute("SELECT id, name, subsite_id FROM whatsapp_template_presets")
            rows = cursor.fetchall()
            for r in rows:
                print(r)
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    debug_templates()

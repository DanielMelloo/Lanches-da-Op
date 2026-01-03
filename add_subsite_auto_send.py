import pymysql

def migrate():
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
            # Check if column exists
            cursor.execute("SHOW COLUMNS FROM subsites LIKE 'auto_send_whatsapp'")
            if cursor.fetchone():
                print("Column 'auto_send_whatsapp' already exists.")
            else:
                print("Adding column 'auto_send_whatsapp'...")
                cursor.execute("ALTER TABLE subsites ADD COLUMN auto_send_whatsapp BOOLEAN DEFAULT TRUE")
                # Update existing rows to True
                cursor.execute("UPDATE subsites SET auto_send_whatsapp = TRUE")
                conn.commit()
                print("Success.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    migrate()

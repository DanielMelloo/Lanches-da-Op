import pymysql

def debug_columns():
    host = '127.0.0.1'
    port = 3307
    user = 'root'
    password = 'CodeEz4ever'
    db_name = 'lanches_da_op'
    
    conn = pymysql.connect(
        host=host, port=port, user=user, password=password, database=db_name,
        cursorclass=pymysql.cursors.DictCursor
    )
    with conn.cursor() as cursor:
        print("--- Columns in orders ---")
        cursor.execute("SHOW COLUMNS FROM orders")
        for r in cursor.fetchall():
            print(f"{r['Field']} - {r['Type']}")

    conn.close()

if __name__ == "__main__":
    debug_columns()

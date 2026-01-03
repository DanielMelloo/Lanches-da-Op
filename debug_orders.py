import pymysql

def debug_orders():
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
        print("--- ID Mismatch Check ---")
        cursor.execute("SELECT id, subsite_id, whatsapp_dispatched FROM orders WHERE id=8")
        o = cursor.fetchone()
        print(f"Order 8: {o}")
        print(f"Subsite ID Type: {type(o['subsite_id'])}, Repr: {repr(o['subsite_id'])}")
        
        cursor.execute("SELECT id, name FROM subsites WHERE id=1")
        s1 = cursor.fetchone()
        print(f"Subsite 1: {s1}")

    conn.close()

if __name__ == "__main__":
    debug_orders()

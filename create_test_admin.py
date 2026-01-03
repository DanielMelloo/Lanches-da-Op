import pymysql
from werkzeug.security import generate_password_hash

def create_admin():
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
            # Check if user exists
            cursor.execute("SELECT * FROM users WHERE petro_key='TEST'")
            if cursor.fetchone():
                print("User TEST already exists. Updating password...")
                cursor.execute("UPDATE users SET password_hash=%s, role='admin', subsite_id=11 WHERE petro_key='TEST'", (generate_password_hash('123'),))
            else:
                print("Creating TEST user...")
                cursor.execute(
                    "INSERT INTO users (petro_key, password_hash, name, role, subsite_id) VALUES (%s, %s, %s, %s, %s)",
                    ('TEST', generate_password_hash('123'), 'Dev Test', 'admin', 11)
                )
            conn.commit()
            print("Success.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    create_admin()

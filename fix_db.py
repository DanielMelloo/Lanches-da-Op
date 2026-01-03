from app import create_app
import pymysql
import re

app = create_app()

uri = app.config['SQLALCHEMY_DATABASE_URI']
# Format: mysql+pymysql://user:pass@host/db
# Regex to parse
match = re.match(r'mysql\+pymysql://([^:]+):([^@]+)@([^/]+)/(.+)', uri)

if not match:
    # Try format without password?
    match_nopass = re.match(r'mysql\+pymysql://([^@]+)@([^/]+)/(.+)', uri)
    if match_nopass:
        user = match_nopass.group(1)
        password = ''
        host = match_nopass.group(2)
        db_name = match_nopass.group(3)
    else:
        print("Could not parse URI:", uri)
        exit(1)
else:
    user = match.group(1)
    password = match.group(2)
    host = match.group(3)
    db_name = match.group(4)

print(f"Connecting to {host} as {user} to fix DB {db_name}...")

try:
    conn = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=db_name,
        cursorclass=pymysql.cursors.DictCursor
    )
    
    with conn.cursor() as cursor:
        sql = """
        CREATE TABLE IF NOT EXISTS whatsapp_template_presets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            content TEXT NOT NULL,
            subsite_id INT NOT NULL,
            FOREIGN KEY (subsite_id) REFERENCES subsites(id) ON DELETE CASCADE
        );
        """
        cursor.execute(sql)
        conn.commit()
        print("SUCCESS: Table 'whatsapp_template_presets' created/verified.")
        
    conn.close()

except Exception as e:
    print(f"FAILURE connecting to {db_name}: {e}")
    
    # Fallback: List databases
    try:
        print("Attempting to list databases...")
        # Connect without DB
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            cursorclass=pymysql.cursors.DictCursor
        )
        with conn.cursor() as cursor:
            cursor.execute("SHOW DATABASES;")
            dbs = [row['Database'] for row in cursor.fetchall()]
            print(f"Available Databases: {dbs}")
            
            # Try to find a good candidate
            candidates = ['lanches_db', 'lanches', 'op_lanches', 'lanches_op']
            target = None
            for c in candidates:
                if c in dbs:
                    target = c
                    break
            
            if target:
                print(f"Found candidate DB: {target}. Attempting to fix...")
                conn.select_db(target)
                sql = """
                CREATE TABLE IF NOT EXISTS whatsapp_template_presets (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    content TEXT NOT NULL,
                    subsite_id INT NOT NULL,
                    FOREIGN KEY (subsite_id) REFERENCES subsites(id) ON DELETE CASCADE
                );
                """
                cursor.execute(sql)
                conn.commit()
                print(f"SUCCESS: Table created in {target}.")
            else:
                print("Could not find a suitable database candidate.")
                
        conn.close()

    except Exception as e2:
         print(f"FATAL ERROR: {e2}")

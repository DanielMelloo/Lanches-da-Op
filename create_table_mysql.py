import pymysql
import os

try:
    print("Connecting to MySQL...")
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='lanches_db',
        cursorclass=pymysql.cursors.DictCursor
    )
    print("Connected.")
    
    with conn.cursor() as cursor:
        sql = """
        CREATE TABLE IF NOT EXISTS whatsapp_template_presets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            content TEXT NOT NULL,
            subsite_id INT NOT NULL,
            FOREIGN KEY (subsite_id) REFERENCES subsites(id)
        );
        """
        print("Executing CREATE TABLE...")
        cursor.execute(sql)
        conn.commit()
        print("Table 'whatsapp_template_presets' created (or already exists).")
        
    conn.close()
except Exception as e:
    print(f"ERROR: {e}")

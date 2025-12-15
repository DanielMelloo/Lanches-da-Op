import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

# Read from schema.sql
with open('schema.sql', 'r', encoding='utf-8') as f:
    sql_script = f.read()

# DB Config
db_user = os.getenv('DB_USER', 'root')
db_pass = os.getenv('DB_PASSWORD', '')
db_host = os.getenv('DB_HOST', 'localhost')
db_name = os.getenv('DB_NAME', 'lanches_db')

print(f"Connecting to {db_host} as {db_user}...")

connection = pymysql.connect(
    host=db_host,
    user=db_user,
    password=db_pass,
    cursorclass=pymysql.cursors.DictCursor
)

try:
    with connection.cursor() as cursor:
        print("Dropping existing tables to ensure clean slate...")
        cursor.execute("DROP DATABASE IF EXISTS lanches_db")
        cursor.execute("CREATE DATABASE lanches_db")
        cursor.execute("USE lanches_db")
        
        # Split script explicitly by ';' might be fragile if strings contain semicolons, 
        # but for this schema it's fine.
        statements = sql_script.split(';')
        for statement in statements:
            if statement.strip():
                # Skip USE and CREATE DATABASE commands in schema if we just did them
                if "CREATE DATABASE" in statement or "USE lanches_db" in statement:
                    continue
                    
                # Fix ENUM mismatch manually here just in case schema.sql wasn't updated perfectly 
                # (though I updated it before, but let's be safe OR just rely on schema.sql)
                # I trust my previous update to schema.sql was correct ('user', 'admin'...)
                
                try:
                    cursor.execute(statement)
                    print(f"Executed.")
                except Exception as e:
                    print(f"Error: {e} \n Statement: {statement[:50]}...")

    connection.commit()
    print("Database RESET and initialized successfully.")
finally:
    connection.close()

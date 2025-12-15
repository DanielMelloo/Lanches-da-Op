from dotenv import load_dotenv
import os

print(f"Current CWD: {os.getcwd()}")
print(f"Env file exists? {os.path.exists('.env')}")

load_dotenv()
print(f"DB_PASSWORD from env: '{os.getenv('DB_PASSWORD')}'")

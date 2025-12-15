import os
import requests
import base64
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
EFI_CLIENT_ID = os.getenv('EFI_CLIENT_ID')
EFI_CLIENT_SECRET = os.getenv('EFI_CLIENT_SECRET')
EFI_CERT_NAME = os.getenv('EFI_CERT_PEM_PRODUCAO') # User said prod credentials
EFI_PIX_KEY = os.getenv('EFI_PIX_KEY')

# Absolute path for certificate
CERT_PATH = os.path.join(os.getcwd(), EFI_CERT_NAME)

print(f"--- Configuration ---")
print(f"Client ID: {EFI_CLIENT_ID[:5]}...{EFI_CLIENT_ID[-5:] if EFI_CLIENT_ID else ''}")
print(f"Cert Path: {CERT_PATH}")
print(f"Exists? {os.path.exists(CERT_PATH)}")
print(f"Pix Key: {EFI_PIX_KEY}")
print(f"---------------------")

def authenticate():
    url = "https://pix.api.efipay.com.br/oauth/token" # PRODUCTION URL
    
    credentials = f"{EFI_CLIENT_ID}:{EFI_CLIENT_SECRET}"
    auth_str = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_str}',
        'Content-Type': 'application/json'
    }
    data = {'grant_type': 'client_credentials'}
    
    print("\nAuthenticating...")
    try:
        response = requests.post(url, headers=headers, json=data, cert=CERT_PATH)
        if response.status_code == 200:
            print("Authentication Successful!")
            return response.json()['access_token']
        else:
            print(f"Auth Failed: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Auth Exception: {e}")
        return None

def create_charge(token):
    if not token: return
    
    url = "https://pix.api.efipay.com.br/v2/cob" # PRODUCTION URL
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # 0.01 Real Charge
    payload = {
        "calendario": {
            "expiracao": 3600
        },
        "valor": {
            "original": "0.01"
        },
        "chave": EFI_PIX_KEY,
        "solicitacaoPagador": "Teste Sistema - Novo Lanches OP"
    }
    
    print("\nCreating Charge...")
    try:
        response = requests.post(url, headers=headers, json=payload, cert=CERT_PATH)
        if response.status_code == 201:
            data = response.json()
            print("\n>>> CHARGE CREATED SUCCESSFULLY <<<")
            print(f"TXID: {data.get('txid')}")
            print(f"PIX COPY & PASTE: {data.get('pixCopiaECola')}")
            
            # Generate QR Code image link (optional, depends on library, but CopyPaste is key)
            print("To test, copy the code above and pay R$ 0.01 in your bank app.")
        else:
            print(f"Charge Creation Failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Charge Exception: {e}")

if __name__ == "__main__":
    token = authenticate()
    if token:
        create_charge(token)

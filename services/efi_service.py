import os
import requests
import base64
import json
from datetime import datetime, timedelta

class EfiService:
    _instance = None
    _token = None
    _token_expiry = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EfiService, cls).__new__(cls)
        return cls._instance

    def _get_credentials(self, subsite):
        # Check if DB has credentials configured
        if subsite.efi_client_id and subsite.efi_pix_key:
            # Use DB Config
            mode = subsite.efi_mode or 'producao'
            client_id = subsite.efi_client_id
            client_secret = subsite.efi_client_secret
            pix_key = subsite.efi_pix_key
            cert_name = subsite.efi_cert_name
                 
            from flask import current_app
            cert_path = os.path.join(current_app.root_path, 'certs', cert_name) if cert_name else None
            base_url = "https://pix.api.efipay.com.br" if mode == 'producao' else "https://pix-h.api.efipay.com.br"
            
            return {
                'client_id': client_id,
                'client_secret': client_secret,
                'pix_key': pix_key,
                'cert_path': cert_path,
                'base_url': base_url
            }
        else:
            # Fallback to ENV
            return self._get_credentials_env()


    def _get_credentials_env(self):
        # Legacy/Fallback
        from flask import current_app
        mode = os.environ.get('EFI_MODE', 'producao')
        client_id = os.environ.get('EFI_CLIENT_ID')
        client_secret = os.environ.get('EFI_CLIENT_SECRET')
        pix_key = os.environ.get('EFI_PIX_KEY')
        
        cert_name = os.environ.get('EFI_CERT_PEM_PRODUCAO') if mode == 'producao' else os.environ.get('EFI_CERT_PEM_HOMOLOGACAO')
        cert_path = os.path.join(current_app.root_path, cert_name) if cert_name else None

        base_url = "https://pix.api.efipay.com.br" if mode == 'producao' else "https://pix-h.api.efipay.com.br"
        return {
            'client_id': client_id,
            'client_secret': client_secret,
            'pix_key': pix_key,
            'cert_path': cert_path,
            'base_url': base_url
        }

    def authenticate(self, subsite):
        # Check if current token is valid (Naive singleton: assumes 1 subsite active generally)
        # TODO: If multi-tenant with diff keys, strictly need dict of tokens keyed by subsite_id
        if self._token and self._token_expiry and datetime.now() < self._token_expiry:
             # Basic check: usually works if keys didn't change. 
             # Ideally check if token matches subsite creds hash. For now simple.
             return self._token

        creds = self._get_credentials(subsite)
        if not creds or not all([creds['client_id'], creds['client_secret'], creds['cert_path']]):
            print("EFI Service: Missing credentials for subsite.")
            return None

        auth_str = base64.b64encode(f"{creds['client_id']}:{creds['client_secret']}".encode()).decode()
        
        url = f"{creds['base_url']}/oauth/token"
        headers = {
            'Authorization': f'Basic {auth_str}',
            'Content-Type': 'application/json'
        }
        data = {'grant_type': 'client_credentials'}

        try:
            response = requests.post(url, headers=headers, json=data, cert=creds['cert_path'])
            if response.status_code == 200:
                data = response.json()
                self._token = data['access_token']
                self._token_expiry = datetime.now() + timedelta(seconds=3500) 
                return self._token
            else:
                print(f"EFI Auth Failed: {response.text}")
                return None
        except Exception as e:
            print(f"EFI Auth Error: {e}")
            return None

    def create_charge(self, order):
        # Uses order.subsite for credentials
        token = self.authenticate(order.subsite)
        if not token: return None

        creds = self._get_credentials(order.subsite)
        url = f"{creds['base_url']}/v2/cob"
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Format Value (Must be string with 2 decimals)
        val_str = "{:.2f}".format(order.total_general)
        
        # Test Override (as requested in test script, keep dynamic for real app unless flagged)
        # val_str = "0.01" # REMOVE THIS FOR PRODUCTION unless hardcoded requested

        payload = {
            "calendario": {"expiracao": 3600},
            "valor": {"original": val_str},
            "chave": creds['pix_key'],
            "solicitacaoPagador": f"Pedido #{order.id}"
        }
        
        # Only include devedor if CPF/CNPJ is available, otherwise schema fails (oneOf validation)
        if hasattr(order.user, 'cpf') and order.user.cpf:
             payload['devedor'] = {
                 "nome": order.user.name or "Cliente",
                 "cpf": order.user.cpf
             }

        try:
            response = requests.post(url, headers=headers, json=payload, cert=creds['cert_path'])
            if response.status_code == 201:
                return response.json()
            else:
                print(f"EFI Charge Failed: {response.text}")
                return None
        except Exception as e:
            print(f"EFI Charge Error: {e}")
            return None

    def check_status(self, subsite, txid):
        token = self.authenticate(subsite)
        if not token: return None

        creds = self._get_credentials(subsite)
        url = f"{creds['base_url']}/v2/cob/{txid}"
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.get(url, headers=headers, cert=creds['cert_path'])
            if response.status_code == 200:
                data = response.json()
                return data.get('status') # ATIVA, CONCLUIDA, REMOVIDA_PELO_USUARIO_RECEBEDOR, REMOVIDA_PELO_PSP
            return None
        except Exception as e:
            print(f"EFI Check Status Error: {e}")
            return None

    def get_qr_code_image(self, app, loc_id):
        # Helper to get base64 image if needed
        token = self.authenticate(app)
        if not token: return None

        creds = self._get_credentials(app)
        url = f"{creds['base_url']}/v2/loc/{loc_id}/qrcode"
        headers = {'Authorization': f'Bearer {token}'}
        
        try:
            response = requests.get(url, headers=headers, cert=creds['cert_path'])
            if response.status_code == 200:
                return response.json().get('imagem')
            return None
        except Exception as e:
            return None

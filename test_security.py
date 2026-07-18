import os
# Prevent scheduler from starting in testing process
os.environ['SKIP_SCHEDULER'] = 'true'
os.environ['SECRET_KEY'] = 'test-secret'

import unittest
from werkzeug.security import generate_password_hash
import json

from app import create_app, db
from models import User, Subsite, Order, Store, Item, Status

class SecurityTestCase(unittest.TestCase):
    def setUp(self):
        # Override SQLAlchemy database URI to sqlite memory before init_db
        self.app = create_app(config_overrides={
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False
        })
        self.client = self.app.test_client()
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.create_all()
        
        # Populate basic entities
        self.sub1 = Subsite(id=1, name="Subsite 1", active=True)
        self.sub2 = Subsite(id=2, name="Subsite 2", active=True)
        db.session.add(self.sub1)
        db.session.add(self.sub2)
        
        self.admin1 = User(
            id=1,
            name="Admin One",
            petro_key="ADM1",
            role="admin",
            subsite_id=1,
            password_hash=generate_password_hash("pass123"),
            active=True
        )
        self.admin2 = User(
            id=2,
            name="Admin Two",
            petro_key="ADM2",
            role="admin",
            subsite_id=2,
            password_hash=generate_password_hash("pass123"),
            active=True
        )
        db.session.add(self.admin1)
        db.session.add(self.admin2)
        
        # Add basic statuses
        self.status_pending = Status(id=1, name="Pendente")
        self.status_paid = Status(id=2, name="Pagamento Confirmado")
        db.session.add(self.status_pending)
        db.session.add(self.status_paid)
        
        # Add stores
        self.store1 = Store(id=1, name="Store One", subsite_id=1, active=True)
        self.store2 = Store(id=2, name="Store Two", subsite_id=2, active=True)
        db.session.add(self.store1)
        db.session.add(self.store2)
        
        # Add items
        self.item1 = Item(id=1, name="Item One", store_id=1, price=10.0, active=True)
        self.item2 = Item(id=2, name="Item Two", store_id=2, price=20.0, active=True)
        db.session.add(self.item1)
        db.session.add(self.item2)

        # Add orders with valid user_id
        self.order1 = Order(
            id=101,
            user_id=1,
            subsite_id=1,
            payment_status="pending",
            status_id=1,
            total_items=10.0,
            tax_fixed=2.0,
            service_fee=1.0,
            total_general=13.0
        )
        self.order2 = Order(
            id=102,
            user_id=2,
            subsite_id=2,
            payment_status="pending",
            status_id=1,
            total_items=20.0,
            tax_fixed=2.0,
            service_fee=1.0,
            total_general=23.0
        )
        db.session.add(self.order1)
        db.session.add(self.order2)
        
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def log_in_user(self, user_id):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['_fresh'] = True

    # --- Test CSRF Protection ---
    def test_csrf_headers_post(self):
        self.log_in_user(1)
        # 1. No Origin/Referer header -> passes
        res = self.client.post("/admin/order/101/update_status", data={"status_id": "2"}, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        
        # 2. Matching Referer -> passes
        res = self.client.post(
            "/admin/order/101/update_status", 
            data={"status_id": "2"}, 
            headers={"Referer": "http://localhost/admin/order/101/details"},
            follow_redirects=False
        )
        self.assertEqual(res.status_code, 302)
        
        # 3. Mismatching Referer -> blocks with 400
        res = self.client.post(
            "/admin/order/101/update_status", 
            data={"status_id": "2"}, 
            headers={"Referer": "http://attacker.com/somepage"},
            follow_redirects=False
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("CSRF verification failed", res.text)

    # --- Test IDOR Protection ---
    def test_idor_order_details(self):
        # Admin 1 tries to view order 101 -> SUCCESS (200)
        self.log_in_user(1)
        res = self.client.get("/admin/order/101/details")
        self.assertEqual(res.status_code, 200)
        
        # Admin 1 tries to view order 102 -> FORBIDDEN (403)
        res = self.client.get("/admin/order/102/details")
        self.assertEqual(res.status_code, 403)

    def test_idor_order_delete(self):
        # Admin 1 tries to delete order 102 -> FORBIDDEN (403)
        self.log_in_user(1)
        res = self.client.post("/admin/order/102/delete")
        self.assertEqual(res.status_code, 403)

    def test_idor_item_delete(self):
        # Admin 1 tries to delete item 2 -> FORBIDDEN (403)
        self.log_in_user(1)
        res = self.client.post("/admin/item/2/delete")
        self.assertEqual(res.status_code, 403)

    # --- Test Webhook IP Whitelisting ---
    def test_webhook_ip_whitelisting(self):
        # 1. From whitelisted IP (127.0.0.1) -> Success (200)
        res = self.client.post(
            "/webhook/efi", 
            json={"pix": [{"txid": "test_tx", "valor": "10.00"}]},
            environ_overrides={"REMOTE_ADDR": "127.0.0.1"}
        )
        self.assertEqual(res.status_code, 200)
        
        # 2. From non-whitelisted IP (200.200.200.200) -> Unauthorized (403)
        res = self.client.post(
            "/webhook/efi", 
            json={"pix": [{"txid": "test_tx", "valor": "10.00"}]},
            environ_overrides={"REMOTE_ADDR": "200.200.200.200"}
        )
        self.assertEqual(res.status_code, 403)

    # --- Test Certificate Upload Extension Whitelist ---
    def test_cert_upload_extension(self):
        self.log_in_user(1)
        from io import BytesIO
        
        # 1. Upload valid .pem -> Passes (Redirects to efi-config)
        data = {
            'efi_cert_file': (BytesIO(b"dummy cert data"), 'cert.pem')
        }
        res = self.client.post("/admin/efi-config/save", data=data)
        self.assertEqual(res.status_code, 302)
        self.assertIn("efi-config", res.headers.get("Location"))
        
        # 2. Upload invalid .py -> Blocks (Redirects and flashes error)
        data = {
            'efi_cert_file': (BytesIO(b"print('hack')"), 'malicious.py')
        }
        res = self.client.post("/admin/efi-config/save", data=data, follow_redirects=True)
        self.assertIn("Apenas", res.text)
        
if __name__ == "__main__":
    unittest.main()

import os
from app import create_app
from database import db

app = create_app()

with app.app_context():
    try:
        # Add columns if not exist
        cols = [
            "efi_active BOOLEAN DEFAULT 1",
            "efi_mode VARCHAR(20) DEFAULT 'producao'",
            "efi_client_id VARCHAR(255)",
            "efi_client_secret VARCHAR(255)",
            "efi_pix_key VARCHAR(255)",
            "efi_cert_name VARCHAR(255)",
            "payment_check_interval INT DEFAULT 30",
            "enable_auto_check BOOLEAN DEFAULT 1"
        ]
        for col in cols:
            try:
                db.session.execute(db.text(f"ALTER TABLE subsites ADD COLUMN {col};"))
                db.session.commit()
                print(f"✓ Added column: {col.split()[0]}")
            except Exception as e:
                db.session.rollback()
                if "Duplicate column name" in str(e) or "already exists" in str(e):
                    print(f"• Column {col.split()[0]} already exists")
                else:
                    print(f"• Error with {col.split()[0]}: {e}")
                    
        # Migration: Copy from ENV to DB for first subsite found
        from models import Subsite
        subsite = Subsite.query.first()
        if subsite:
            subsite.efi_client_id = os.getenv('EFI_CLIENT_ID')
            subsite.efi_client_secret = os.getenv('EFI_CLIENT_SECRET')
            subsite.efi_pix_key = os.getenv('EFI_PIX_KEY')
            subsite.efi_mode = os.getenv('EFI_MODE', 'producao')
            # Cert logic: pick based on mode
            if subsite.efi_mode == 'producao':
                 cert = os.getenv('EFI_CERT_PEM_PRODUCAO')
            else:
                 cert = os.getenv('EFI_CERT_PEM_HOMOLOGACAO')
            if cert and '/' in cert: 
                 subsite.efi_cert_name = cert.split('/')[-1]
            elif cert:
                 subsite.efi_cert_name = cert
            
            db.session.commit()
            print(f"\n✓ Schema updated and ENV migrated to Subsite '{subsite.name}'")
        else:
            print("\n✓ Schema updated but no subsite found to migrate ENV.")
            
    except Exception as e:
        print(f"❌ Error updating schema: {e}")
        import traceback
        traceback.print_exc()

print("\nMigração concluída! Pode testar agora.")

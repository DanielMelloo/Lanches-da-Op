from extensions import scheduler
from models import Order, Status
from services.efi_service import EfiService
from database import db

def check_all_pending_payments():
    """
    Background task to check status of ALL pending PIX orders.
    """
    # Use scheduler.app to get the real app instance
    with scheduler.app.app_context():
        # Find all pending orders that have a PIX charge ID
        pending_orders = Order.query.filter(
            Order.payment_status == 'pending',
            Order.pix_charge_id != None
        ).all()
        
        if not pending_orders:
            return

        service = EfiService()
        updated_count = 0
        
        for order in pending_orders:
            try:
                # Provide subsite-aware check
                status_efi = service.check_status(order.subsite, order.pix_charge_id)
                if status_efi == 'CONCLUIDA':
                    paid_status = Status.query.filter_by(name='Pagamento Confirmado').first()
                    if not paid_status: 
                        paid_status = order.status 
                    
                    order.status = paid_status
                    order.payment_status = 'approved'
                    updated_count += 1
                    print(f"[Background] Order #{order.id} confirmed!")
            except Exception as e:
                print(f"[Background] Error checking Order #{order.id}: {e}")
        
        if updated_count > 0:
            db.session.commit()

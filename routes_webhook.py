from flask import Blueprint, request, current_app
from models import Order, Status
from database import db
import json

webhook_bp = Blueprint('webhook', __name__, url_prefix='/webhook')

# Endereços IP oficiais da EFí para envio de webhooks (e localhost para testes)
EFI_WEBHOOK_IPS = {
    "34.193.116.226",
    "54.224.237.234",
    "18.230.114.225",
    "54.94.120.224",
    "127.0.0.1",
    "localhost",
    "::1"
}

@webhook_bp.route('/efi', methods=['POST'])
def efi_webhook():
    """
    Webhook da EFí para notificações PIX.
    Chamado automaticamente quando um PIX é pago.
    """
    try:
        # Validar IP de origem (considerando cabeçalho X-Forwarded-For do proxy reverso Nginx)
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
            
        if client_ip not in EFI_WEBHOOK_IPS:
            current_app.logger.warning(f"Tentativa de webhook bloqueada do IP: {client_ip}")
            return {'status': 'unauthorized'}, 403

        # Log do webhook recebido
        payload = request.get_json()
        current_app.logger.info(f"EFí Webhook received: {json.dumps(payload)}")
        
        # Formato do webhook EFí PIX:
        # { "pix": [ { "txid": "...", "valor": "10.00", ... } ] }
        
        if 'pix' not in payload:
            current_app.logger.warning("Webhook sem campo 'pix'")
            return {'status': 'ignored'}, 200
        
        pix_list = payload['pix']
        updated_count = 0
        
        for pix_event in pix_list:
            txid = pix_event.get('txid')
            if not txid:
                continue
                
            # Buscar pedido por pix_charge_id (que é o txid)
            order = Order.query.filter_by(pix_charge_id=txid).first()
            
            if not order:
                current_app.logger.warning(f"Order not found for txid: {txid}")
                continue
            
            # Se já foi pago, ignorar
            if order.payment_status == 'approved':
                continue
            
            # Atualizar para pago
            paid_status = Status.query.filter_by(name='Pedido Confirmado').first() # Was Pagamento Confirmado
            if paid_status:
                order.status = paid_status
            
            order.payment_status = 'approved'
            updated_count += 1
            
            current_app.logger.info(f"✅ Order #{order.id} marked as PAID via webhook (txid: {txid})")
        
        if updated_count > 0:
            db.session.commit()
            
        return {'status': 'ok', 'processed': updated_count}, 200
        
    except Exception as e:
        current_app.logger.error(f"Webhook error: {e}")
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'message': str(e)}, 500

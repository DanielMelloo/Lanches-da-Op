from models import Subsite, Order, Status
from database import db
from datetime import datetime

def recalculate_taxes(subsite_id):
    """
    Recalculates the tax for all eligible orders in a subsite running in 'variable' tax mode.
    Eligible Orders: Not Cancelled, Not Paid (Payment Status != approved).
    Formula: Daily Goal / Count of Eligible Orders.
    """
    subsite = Subsite.query.get(subsite_id)
    if not subsite or subsite.tax_mode != 'variable':
        return

    # 1. Get Daily Goal
    settings = subsite.variable_tax_settings or {}
    daily_goal = float(settings.get('daily_goal', 0.0))
    
    # 2. Find eligible orders (Active & Unpaid)
    # Exclude Cancelled (assuming status_id 4 is Cancelled, need to verify or use name)
    # We filter by payment_status != 'approved' because paid orders shouldn't change price.
    
    # Get Cancelled Status ID
    cancelled_status = Status.query.filter_by(name='Cancelado').first()
    cancelled_id = cancelled_status.id if cancelled_status else 4 # fallback

    query = Order.query.filter(
        Order.subsite_id == subsite_id,
        Order.status_id != cancelled_id,
        Order.payment_status != 'approved'
    )
    
    eligible_orders = query.all()
    count = len(eligible_orders)
    
    # 3. Calculate New Tax
    new_tax = 0.0
    if count > 0:
        new_tax = daily_goal / count
    
    # Update Subsite Reference Value
    subsite.calculated_variable_tax = new_tax
    
    # 4. Apply to Orders
    for order in eligible_orders:
        order.tax_fixed = new_tax
        
        # Recalculate Totals
        # Logic: Total General = (Items + Tax) * Markup (if applicable)
        
        total_items = order.total_items
        markup = 1.0
        
        # Check if "Repassar Taxa Pix" is enabled
        # We use the new field pass_pix_tax if available, or fallback to older logic if needed (but now we have the field)
        # Note: Order doesn't snapshot the markup decision, maybe it should? 
        # For now, we use current subsite setting.
        if hasattr(subsite, 'pass_pix_tax') and subsite.pass_pix_tax:
             markup = 1.013
        
        total_with_tax = total_items + new_tax
        order.total_general = total_with_tax * markup
        
        # Service Fee is difference
        order.service_fee = order.total_general - total_items
        
    db.session.commit()
    print(f"Recalculated Taxes for Subsite {subsite_id}: Goal={daily_goal}, Count={count}, Tax={new_tax:.2f}")

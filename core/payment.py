"""
— Razorpay integration for Bot order system.

Handles:
    - Creating Razorpay orders
    - Generating payment links
    - QR code URLs
    - Verifying webhook signatures
"""

import hmac
import hashlib
import logging
import razorpay
from django.conf import settings

logger = logging.getLogger(__name__)

def _get_client():
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

def create_razorpay_order(order) -> dict:
    """
    Create a Razorpay order for the given Order instance.
    Return the Razorpay order dict or None on failure.
    """
    try:
        client = _get_client()
        amount_paise = int(order.total_amount * 100)  # Razorpay uses paise

        rz_order = client.order.create({
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': str(order.order_id)[:40],
            'notes':{
                'customer_name': order.user.full_name,
                'customer_phone': order.user.contact_number,
                'delivery_address': order.user.address,
            }
        })
        logger.info(f"Created Razorpay order {rz_order['id']} for Order {order.order_id}")
        return rz_order
    
    except Exception as e:
        logger.error(f"Razorpay order created: {rz_order['id']} for Order {order.order_id}")
        return rz_order
    
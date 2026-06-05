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
    
def get_payment_link(order) -> str | None:
    """
    Creates Razorpay Payment Link and returns the short URL
    This link can be sent via Whatsapp for easy payment.
    """
    try:
        client = _get_client()
        amount_paise = int(order.total_amount * 100)

        payload = {
            'amount': amount_paise,
            'currency': 'INR',
            'accept_partial': False,
            'description': f'bot for Order #{str(order.order_id)[:8].upper()}',
            'customer': {
                'name': order.user.full_name,
                'contact': order.user.contact_number,
            },
            'notify': {
                'sms': True,
                'email': False
            },
            'reminder_enable': False,
            'notes':{
                'order_uuid': str(order.order_id),
            },
            'callback_url': f"{settings.BASE_URL}/payment/callback/",
            'callback_method': 'get'   
        }

        link = client.payment_link.create(payload)
        logger.info(f"Payment link created: {link['short_url']}")
        return link.get('short_url')
    
    except Exception as e:
        logger.error(f"Payment link creation failed: {e}")
        return None
    
def get_payment_qr_url(razorpay_order_id: str) -> str | None:
    """
    Generate a UPI QR code image URL via Razorpay
    Returns a hosted image URL or None
    """

    try:
        client = _get_client()
        qr = client.qrcode.create({
            'type': 'upi_qr',
            'name': 'Bot Restaurant',
            'usage': 'single_use',
            'fixed_amount': True,
            'payment_amount': None, #linked via order
            'description': f"order {razorpay_order_id}",
            'close_by': None,
        })
        return qr.get('image_url')
    except Exception as e:
        logger.warning(f"Qr code generation failed (non-critical): {e}")
        return None

def verify_webhook_signature(payload_body: bytes, signature: str) -> bool:
    """
    Verifies the Razorpay webhook signature using HMAC-SHA256.
    call this in the webhook view before processing
    """
    secret = settings.RAZORPAY_WEBHOOK_SECRET.encode('utf-8')
    expected = hmac.new(secret, payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


"""
Reusable helper functions / test data factories.
Import these in any test file instead of repeating setup code.
"""

from decimal import Decimal
from core.models import UserSession, MenuItem, Order, OrderItem


# ── Phone numbers 
PHONE_1 = "whatsapp:+919876543210"
PHONE_2 = "whatsapp:+919123456789"


# ── Menu factory 

def make_menu_item(name="Burger", price="120.00", emoji="🍔", available=True, description="Tasty burger"):
    return MenuItem.objects.create(
        name=name,
        price=Decimal(price),
        emoji=emoji,
        is_available=available,
        description=description,
    )


def make_standard_menu():
    """Create 3 standard menu items used across most tests."""
    burger = make_menu_item("Chicken Burger", "120.00", "🍔")
    pizza  = make_menu_item("Veggie Pizza",   "250.00", "🍕")
    fries  = make_menu_item("Masala Fries",    "70.00", "🍟")
    return burger, pizza, fries


# ── User session factory 

def make_session(phone=PHONE_1, state="new", **kwargs):
    return UserSession.objects.create(phone=phone, state=state, **kwargs)


def make_complete_session(phone=PHONE_1):
    """A session with all profile data filled in, ready for menu selection."""
    return UserSession.objects.create(
        phone=phone,
        first_name="Vivek",
        last_name="Sharma",
        address="123 MG Road, Indore 452001",
        contact_number="9876543210",
        state="show_menu",
    )


# ── Order factory 

def make_order(session=None, status="pending", razorpay_order_id="", payment_id=""):
    if session is None:
        session = make_complete_session()
    return Order.objects.create(
        user=session,
        status=status,
        total_amount=Decimal("120.00"),
        razorpay_order_id=razorpay_order_id,
        payment_id=payment_id,
    )


def make_order_with_items(session=None):
    """Order with 2 items already attached."""
    burger, pizza, _ = make_standard_menu()
    if session is None:
        session = make_complete_session()
    order = Order.objects.create(user=session, status="pending")
    OrderItem.objects.create(order=order, item=burger, quantity=1)
    OrderItem.objects.create(order=order, item=pizza,  quantity=2)
    order.calculate_total()   # 120 + 500 = 620
    return order


# ── Twilio POST data builder 

def twilio_post(body: str, phone: str = PHONE_1, num_media: int = 0) -> dict:
    """Build POST data dict that mimics a Twilio WhatsApp webhook call."""
    return {
        "Body":      body,
        "From":      phone,
        "NumMedia":  str(num_media),
        "To":        "whatsapp:+14155238886",
        "MessageSid": "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    }


# ── Razorpay webhook payload builder 

def razorpay_payment_captured_payload(razorpay_order_id: str,
                                    payment_id: str = "pay_test123",
                                    order_uuid: str = "") -> dict:
    return {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id":         payment_id,
                    "order_id":   razorpay_order_id,
                    "amount":     12000,
                    "currency":   "INR",
                    "status":     "captured",
                    "notes": {
                        "order_uuid": order_uuid,
                    }
                }
            }
        }
    }


def razorpay_payment_failed_payload(razorpay_order_id: str) -> dict:
    return {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id":       "pay_failed_001",
                    "order_id": razorpay_order_id,
                    "status":   "failed",
                    "notes":    {}
                }
            }
        }
    }
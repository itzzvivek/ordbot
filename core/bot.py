# Conversation state machine for the whatsapp bot

import re
import logging

from .models import MenuItem, Order, OrderItem, UserSession

logger = logging.getLogger(__name__)


GREETING_KEYWORDS = {'hi', 'hello', 'hey', 'hlo', 'helo', 'start', 'namaste', 'hii', 'sup'}

WELCOME_MSG = (
    "👋 *Welcome to Restaurant!*\n\n"
    "We're delighted to have you here. 🍽️\n"
    "Let's get you set up for ordering.\n\n"
    "What's your *first name*?"
)

HELP_MSG = (
    "🤖 *Restaurant Bot*\n\n"
    "Type *hi* or *hello* to start a new order.\n"
    "Type *menu* to see available items.\n"
    "Type *cancel* to cancel your current order."
)

def greeting(text: str) -> bool:
    return text.lower().strip() in GREETING_KEYWORDS

def _build_menu_text()-> str:
    items = MenuItem.objects.filter(is_available=True).order_by('id')
    if not items.exists():
        return "Sorry, our menu is currently unavailable. Please check back later."
    
    lines = [" 🍽️ *Our Menu*\n"]
    for idx, items in enumerate(items, start=1):
        desc = f"\n _{items.description}_\n" if items.description else ""
        lines.append(f"{idx}. {items.emoji} *{items.name}* - ₹{items.price}{desc}")
    
    lines.append(
        "\n📝 *How to order:*\n"
        "Type item numbers separated by commas.\n"
        "Example: `1, 2, 3` or `1x2, 2x1` (item x quantity)\n\n"
        "Type *done* when finished selecting."
    )

    return "\n".join(lines)


def _parse_order_input(text: str):
    """
    Parse user input like '1, 2, 3' or '1x2, 3x1' into
    {item_index: quantity} dict (1-based indices).
    Returns None if unparseable.
    """
    text = text.strip().lower().replace(' ', '')
    selections = {}

    # Support both '1,2,3' and '1x2,3x1' formats
    parts = re.split(r'[,;]', text)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        match = re.fullmatch(r'(\d+)x(\d+)?', part) #e.g. 2*3
        if match:
            idx, qty = int(match.group(1)), int(match.group(2))
        elif part.isdigit():
            idx, qty = int(part), 1
        else:
            return None
        selections[idx] = selections.get(idx, 0) + qty

    return selections if selections else None


def _build_order_summary(order: Order) -> str:
    lines = ["🧾 *Your Order Summary*\n"]
    for oi in order.orderitem_set.select_related('item').all():
        lines.append(f"  • {oi.quantity}x {oi.item.emoji} {oi.item.name}  — ₹{oi.subtotal}")
    lines.append(f"\n💰 *Total: ₹{order.total_amount}*")
    lines.append(
        f"\n📦 *Deliver to:*\n"
        f"  {order.user.full_name}\n"
        f"  {order.user.address}\n"
        f"  📞 {order.user.contact_phone}"
    )
    return "\n".join(lines)

def _build_payment_message(order: Order, qr_url: str = None, payment_link: str = None) -> str:
    msg = (
        f"💳 *Payment Details*\n\n"
        f"Order ID: `{str(order.order_id)[:8].upper()}`\n"
        f"Amount: *₹{order.total_amount}*\n\n"
    )
    if payment_link:
        msg += f"Please complete your payment using the link below:\n{payment_link}\n\n"
    if qr_url:
        msg += f"Or scan the QR code below to pay:\n{qr_url}\n\n"
    msg += (
        "Once payment is confirmed, we'll notify you instantly! ✅\n"
        "Your order will be prepared right away. 🍳"
    )
    return msg


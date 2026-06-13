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


def _is_greeting(text: str) -> bool:
    return text.lower().strip() in GREETING_KEYWORDS


def _build_menu_text() -> str:
    items = MenuItem.objects.filter(is_available=True).order_by('id')
    if not items.exists():
        return "Sorry, our menu is currently unavailable. Please check back later."

    lines = ["🍽️ *Our Menu*\n"]
    for idx, item in enumerate(items, start=1):
        desc = f"\n   _{item.description}_\n" if item.description else ""
        lines.append(f"{idx}. {item.emoji} *{item.name}* - ₹{item.price}{desc}")

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

    parts = re.split(r'[,;]', text)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        match = re.fullmatch(r'(\d+)x(\d+)', part)  # e.g. 2x3
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
        f"  📞 {order.user.contact_number}"  # matches your UserSession field name
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


# Handler for incoming messages
def handle_message(sender_phone: str, incoming_text: str) -> dict:
    """
    Main entry point.
    Returns a dict:
        {
            "text": str,
            "media_url": str | None,
            "payment_link": str | None,
        }
    """
    text = incoming_text.strip()
    text_lower = text.lower()

    response = {'text': '', 'media_url': None, 'payment_link': None}

    # ── Cancel command ──────────────────────────────────────────
    if text_lower == 'cancel':
        session, _ = UserSession.objects.get_or_create(phone=sender_phone)
        Order.objects.filter(user=session, status='pending').update(status='cancelled')
        session.state          = 'new'
        session.first_name     = ''
        session.last_name      = ''
        session.address        = ''
        session.contact_number = ''   # matches your model field
        session.save()
        response['text'] = (
            "Your current order has been cancelled.\n\n"
            "If you'd like to start a new order, just say hi! 👋"
        )
        return response

    # ── Get or create session ───────────────────────────────────
    session, created = UserSession.objects.get_or_create(phone=sender_phone)

    # ── Greeting ────────────────────────────────────────────────
    if _is_greeting(text_lower):
        if session.state in ('completed', 'new', ''):
            session.state          = 'ask_firstname'
            session.first_name     = ''
            session.last_name      = ''
            session.address        = ''
            session.contact_number = ''   # matches your model field
            session.save()
            response['text'] = WELCOME_MSG
        else:
            response['text'] = (
                f"👋 Hey {session.first_name or 'there'}! "
                f"You have an order in progress.\n\n"
                f"Type *cancel* to restart or continue from where you left off."
            )
        return response

    # ── State machine ────────────────────────────────────────────
    state = session.state.strip()

    # New user who didn't say hi
    if state == 'new':
        response['text'] = HELP_MSG
        return response

    # ASK FIRST NAME
    if state == 'ask_firstname':
        if len(text) < 2:
            response['text'] = "Please enter a valid first name."
            return response
        session.first_name = text.title()
        session.state = 'ask_lastname'
        session.save()
        response['text'] = f"Nice to meet you, *{session.first_name}*! 😊\n\nWhat's your *last name*?"
        return response

    # ASK LAST NAME
    if state == 'ask_lastname':
        if len(text) < 2:
            response['text'] = "Please enter a valid last name."
            return response
        session.last_name = text.title()
        session.state = 'ask_address'
        session.save()
        response['text'] = (
            f"Great, *{session.full_name}*! 🎉\n\n"
            f"📍 Please share your *delivery address*:\n"
            f"_(Include street, area, city and pincode)_"
        )
        return response

    # ASK ADDRESS
    if state == 'ask_address':
        if len(text) < 10:
            response['text'] = "Please enter a complete delivery address (at least 10 characters)."
            return response
        session.address = text
        session.state = 'ask_phone'
        session.save()
        response['text'] = (
            "📞 Almost there! What's your *contact phone number*?\n"
            "_(We'll call you only if needed for delivery)_"
        )
        return response

    # ASK PHONE
    if state == 'ask_phone':
        digits = re.sub(r'\D', '', text)
        if len(digits) < 10:
            response['text'] = "Please enter a valid phone number (at least 10 digits)."
            return response
        session.contact_number = digits   # matches your model field
        session.state = 'show_menu'
        session.save()
        response['text'] = (
            f"✅ *Details saved!*\n\n"
            f"👤 Name: {session.full_name}\n"
            f"📍 Address: {session.address}\n"
            f"📞 Phone: {session.contact_number}\n\n"
            f"Here's our menu! 👇\n\n"
            + _build_menu_text()
        )
        return response

    # SHOW MENU / AWAITING ORDER
    if state in ('show_menu', 'awaiting_order'):
        if text_lower == 'menu':
            response['text'] = _build_menu_text()
            return response

        selections = _parse_order_input(text)
        if not selections:
            response['text'] = (
                "❓ I didn't understand that.\n\n"
                + _build_menu_text()
            )
            return response

        menu_items = list(MenuItem.objects.filter(is_available=True).order_by('id'))
        max_idx = len(menu_items)
        invalid = [i for i in selections if i < 1 or i > max_idx]
        if invalid:
            response['text'] = (
                f"⚠️ Item numbers {invalid} don't exist. Please choose from 1 to {max_idx}.\n\n"
                + _build_menu_text()
            )
            return response

        # Create / replace pending order
        Order.objects.filter(user=session, status='pending').delete()
        order = Order.objects.create(user=session)

        for idx, qty in selections.items():
            item = menu_items[idx - 1]
            OrderItem.objects.create(order=order, item=item, quantity=qty)

        order.calculate_total()
        order.refresh_from_db()
        session.state = 'confirm_order'
        session.save()

        summary = _build_order_summary(order)
        response['text'] = (
            f"{summary}\n\n"
            f"✅ Type *confirm* to proceed to payment.\n"
            f"✏️ Type *menu* to change your order.\n"
            f"❌ Type *cancel* to cancel."
        )
        return response

    # ── CRITICAL FIX: confirm_order must be at TOP LEVEL ─────────
    # (was incorrectly indented inside show_menu block before)
    if state == 'confirm_order':
        if text_lower == 'menu':
            session.state = 'show_menu'
            session.save()
            response['text'] = _build_menu_text()
            return response

        if text_lower != 'confirm':
            response['text'] = (
                "Please type *confirm* to proceed to payment, "
                "*menu* to change your order, or *cancel* to cancel."
            )
            return response

        # Create Razorpay order
        order = Order.objects.filter(user=session, status='pending').last()
        if not order:
            session.state = 'show_menu'
            session.save()
            response['text'] = "Oops! Your order was lost. Please select items again.\n\n" + _build_menu_text()
            return response

        from .payment import create_razorpay_order, get_payment_qr_url, get_payment_link
        rz_order = create_razorpay_order(order)

        if rz_order:
            order.razorpay_order_id = rz_order['id']
            order.save()
            session.state = 'awaiting_payment'
            session.save()

            amount_paise = int(order.total_amount * 100)
            qr_url = get_payment_qr_url(rz_order['id'], amount_paise)
            payment_link = get_payment_link(order)
            response['text'] = _build_payment_message(order, qr_url, payment_link)
            response['media_url'] = qr_url
            response['payment_link'] = payment_link
        else:
            response['text'] = (
                "⚠️ Payment gateway error. Please try again.\n"
                "Type *confirm* to retry."
            )
        return response

    # AWAITING PAYMENT
    if state == 'awaiting_payment':
        order = Order.objects.filter(user=session, status='pending').last()
        if not order:
            response['text'] = (
                "✅ Your order may already be confirmed! "
                "Check for a success message or type *hi* to start a new order."
            )
            return response

        response['text'] = (
            f"⏳ We're waiting for payment confirmation for Order "
            f"`{str(order.order_id)[:8].upper()}`.\n\n"
            f"Once you complete the payment, we'll automatically confirm your order.\n\n"
            f"Type *cancel* if you want to cancel."
        )
        return response

    # COMPLETED
    if state == 'completed':
        response['text'] = (
            "🎉 Your last order was completed!\n\n"
            "Type *hi* to place a new order. 😊"
        )
        return response

    # Fallback
    response['text'] = HELP_MSG
    return response
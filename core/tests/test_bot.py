"""
Unit tests for core/bot.py — the conversation state machine.

Each test class covers one state in the flow:
  new → ask_firstname → ask_lastname → ask_address → ask_phone
      → show_menu → confirm_order → awaiting_payment → completed

"""

from django.test import TestCase
from unittest.mock import patch, MagicMock
from decimal import Decimal

from core.bot import handle_message, _parse_order_input, _is_greeting, _build_menu_text
from core.models import UserSession, MenuItem, Order, OrderItem
from .factories import (
    make_menu_item, make_standard_menu,
    make_session, make_complete_session,
    make_order, make_order_with_items,
    PHONE_1, PHONE_2,
)


#  Helper utils

class IsGreetingTest(TestCase):

    def test_standard_greetings(self):
        for word in ['hi', 'hello', 'hey', 'hii', 'hlo', 'namaste', 'start', 'sup']:
            with self.subTest(word=word):
                self.assertTrue(_is_greeting(word))

    def test_case_insensitive(self):
        self.assertTrue(_is_greeting("HI"))
        self.assertTrue(_is_greeting("Hello"))
        self.assertTrue(_is_greeting("HELLO"))

    def test_not_greeting(self):
        for word in ['burger', '1', 'confirm', 'cancel', 'menu']:
            with self.subTest(word=word):
                self.assertFalse(_is_greeting(word))


class ParseOrderInputTest(TestCase):

    def test_single_item(self):
        result = _parse_order_input("1")
        self.assertEqual(result, {1: 1})

    def test_multiple_items_comma(self):
        result = _parse_order_input("1, 2, 3")
        self.assertEqual(result, {1: 1, 2: 1, 3: 1})

    def test_item_with_quantity(self):
        result = _parse_order_input("1x2")
        self.assertEqual(result, {1: 2})

    def test_mixed_format(self):
        result = _parse_order_input("1x2, 3, 2x1")
        self.assertEqual(result, {1: 2, 3: 1, 2: 1})

    def test_semicolon_separator(self):
        result = _parse_order_input("1;2;3")
        self.assertEqual(result, {1: 1, 2: 1, 3: 1})

    def test_duplicate_item_accumulates(self):
        # 1x2 and then 1 again → total 3 of item 1
        result = _parse_order_input("1x2, 1")
        self.assertEqual(result[1], 3)

    def test_invalid_returns_none(self):
        self.assertIsNone(_parse_order_input("burger"))
        self.assertIsNone(_parse_order_input("abc"))
        self.assertIsNone(_parse_order_input(""))

    def test_spaces_handled(self):
        result = _parse_order_input("  1  ,  2  ")
        self.assertEqual(result, {1: 1, 2: 1})


#  State: new user (no greeting)

class NewUserWithoutGreetingTest(TestCase):

    def test_random_message_shows_help(self):
        result = handle_message(PHONE_1, "what do you sell")
        self.assertIn("hi", result['text'].lower())

    def test_response_has_all_keys(self):
        result = handle_message(PHONE_1, "hello")
        self.assertIn('text', result)
        self.assertIn('media_url', result)
        self.assertIn('payment_link', result)

#  State: greeting → ask_firstname

class GreetingTest(TestCase):

    def test_hi_starts_flow(self):
        result = handle_message(PHONE_1, "hi")
        self.assertIn("first name", result['text'].lower())
        session = UserSession.objects.get(phone=PHONE_1)
        self.assertEqual(session.state, "ask_firstname")

    def test_hello_starts_flow(self):
        result = handle_message(PHONE_1, "hello")
        self.assertIn("first name", result['text'].lower())

    def test_hey_starts_flow(self):
        result = handle_message(PHONE_1, "hey")
        self.assertIn("first name", result['text'].lower())

    def test_namaste_starts_flow(self):
        result = handle_message(PHONE_1, "namaste")
        self.assertIn("first name", result['text'].lower())

    def test_uppercase_greeting(self):
        result = handle_message(PHONE_1, "HI")
        self.assertIn("first name", result['text'].lower())

    def test_greeting_mid_flow_shows_warning(self):
        """Greeting during active order should warn, not restart."""
        make_session(PHONE_1, state="ask_lastname", first_name="Vivek")
        result = handle_message(PHONE_1, "hi")
        self.assertIn("in progress", result['text'].lower())
        # State should NOT have changed
        session = UserSession.objects.get(phone=PHONE_1)
        self.assertEqual(session.state, "ask_lastname")

    def test_greeting_after_completed_restarts(self):
        make_session(PHONE_1, state="completed")
        result = handle_message(PHONE_1, "hi")
        self.assertIn("first name", result['text'].lower())
        session = UserSession.objects.get(phone=PHONE_1)
        self.assertEqual(session.state, "ask_firstname")

#  State: ask_firstname

class AskFirstNameTest(TestCase):

    def setUp(self):
        self.session = make_session(PHONE_1, state="ask_firstname")

    def test_valid_first_name_saved(self):
        handle_message(PHONE_1, "Vivek")
        self.session.refresh_from_db()
        self.assertEqual(self.session.first_name, "Vivek")
        self.assertEqual(self.session.state, "ask_lastname")

    def test_name_is_title_cased(self):
        handle_message(PHONE_1, "vivek")
        self.session.refresh_from_db()
        self.assertEqual(self.session.first_name, "Vivek")

    def test_response_asks_last_name(self):
        result = handle_message(PHONE_1, "Vivek")
        self.assertIn("last name", result['text'].lower())

    def test_single_char_rejected(self):
        result = handle_message(PHONE_1, "V")
        self.assertIn("valid", result['text'].lower())
        self.session.refresh_from_db()
        self.assertEqual(self.session.state, "ask_firstname")  # unchanged

    def test_empty_rejected(self):
        result = handle_message(PHONE_1, "")
        self.assertIn("valid", result['text'].lower())

    def test_name_with_spaces(self):
        """Names like 'Mary Jane' are valid."""
        handle_message(PHONE_1, "Mary Jane")
        self.session.refresh_from_db()
        self.assertEqual(self.session.first_name, "Mary Jane")


#  State: ask_lastname

class AskLastNameTest(TestCase):

    def setUp(self):
        self.session = make_session(PHONE_1, state="ask_lastname", first_name="Vivek")

    def test_valid_last_name_saved(self):
        handle_message(PHONE_1, "Sharma")
        self.session.refresh_from_db()
        self.assertEqual(self.session.last_name, "Sharma")
        self.assertEqual(self.session.state, "ask_address")

    def test_response_asks_address(self):
        result = handle_message(PHONE_1, "Sharma")
        self.assertIn("address", result['text'].lower())

    def test_short_last_name_rejected(self):
        result = handle_message(PHONE_1, "S")
        self.session.refresh_from_db()
        self.assertEqual(self.session.state, "ask_lastname")

    def test_full_name_used_in_response(self):
        result = handle_message(PHONE_1, "Sharma")
        self.assertIn("Vivek", result['text'])
        self.assertIn("Sharma", result['text'])

#  State: ask_address

class AskAddressTest(TestCase):

    def setUp(self):
        self.session = make_session(
            PHONE_1, state="ask_address",
            first_name="Vivek", last_name="Sharma"
        )

    def test_valid_address_saved(self):
        addr = "123 MG Road, Indore 452001"
        handle_message(PHONE_1, addr)
        self.session.refresh_from_db()
        self.assertEqual(self.session.address, addr)
        self.assertEqual(self.session.state, "ask_phone")

    def test_response_asks_phone(self):
        result = handle_message(PHONE_1, "123 MG Road, Indore 452001")
        self.assertIn("phone", result['text'].lower())

    def test_short_address_rejected(self):
        result = handle_message(PHONE_1, "MG Road")  # < 10 chars
        self.session.refresh_from_db()
        self.assertEqual(self.session.state, "ask_address")

    def test_exactly_10_chars_accepted(self):
        handle_message(PHONE_1, "1234567890")
        self.session.refresh_from_db()
        self.assertEqual(self.session.state, "ask_phone")

#  State: ask_phone

class AskPhoneTest(TestCase):

    def setUp(self):
        self.session = make_session(
            PHONE_1, state="ask_phone",
            first_name="Vivek", last_name="Sharma",
            address="123 MG Road, Indore 452001"
        )
        make_standard_menu()

    def test_valid_phone_saved(self):
        handle_message(PHONE_1, "9876543210")
        self.session.refresh_from_db()
        self.assertEqual(self.session.contact_number, "9876543210")
        self.assertEqual(self.session.state, "show_menu")

    def test_phone_with_formatting_accepted(self):
        """Formatted phone like +91-98765-43210 should strip to digits."""
        handle_message(PHONE_1, "+91-98765-43210")
        self.session.refresh_from_db()
        self.assertEqual(self.session.contact_number, "919876543210")
        self.assertEqual(self.session.state, "show_menu")

    def test_short_phone_rejected(self):
        result = handle_message(PHONE_1, "12345")
        self.session.refresh_from_db()
        self.assertEqual(self.session.state, "ask_phone")

    def test_response_shows_summary_and_menu(self):
        result = handle_message(PHONE_1, "9876543210")
        self.assertIn("Vivek", result['text'])
        self.assertIn("menu", result['text'].lower())

    def test_response_includes_all_saved_details(self):
        result = handle_message(PHONE_1, "9876543210")
        self.assertIn("Vivek Sharma", result['text'])
        self.assertIn("MG Road", result['text'])


#  State: show_menu / awaiting_order

class ShowMenuTest(TestCase):

    def setUp(self):
        self.session = make_complete_session(PHONE_1)
        self.burger, self.pizza, self.fries = make_standard_menu()

    def test_menu_command_shows_menu(self):
        result = handle_message(PHONE_1, "menu")
        self.assertIn("Chicken Burger", result['text'])
        self.assertIn("Veggie Pizza", result['text'])

    def test_menu_shows_prices(self):
        result = handle_message(PHONE_1, "menu")
        self.assertIn("120", result['text'])
        self.assertIn("250", result['text'])

    def test_menu_not_shown_when_empty(self):
        MenuItem.objects.all().delete()
        result = handle_message(PHONE_1, "menu")
        self.assertIn("unavailable", result['text'].lower())

    def test_valid_single_item_selection(self):
        result = handle_message(PHONE_1, "1")
        self.assertIn("Order Summary", result['text'])
        self.session.refresh_from_db()
        self.assertEqual(self.session.state, "confirm_order")

    def test_multiple_items_selection(self):
        result = handle_message(PHONE_1, "1, 2")
        self.assertIn("Chicken Burger", result['text'])
        self.assertIn("Veggie Pizza", result['text'])

    def test_item_with_quantity(self):
        result = handle_message(PHONE_1, "1x3")
        order = Order.objects.filter(user=self.session).last()
        oi = order.orderitem_set.get(item=self.burger)
        self.assertEqual(oi.quantity, 3)

    def test_order_total_calculated_correctly(self):
        handle_message(PHONE_1, "1x2, 3")   # 120*2 + 70 = 310
        order = Order.objects.filter(user=self.session, status='pending').last()
        self.assertEqual(order.total_amount, Decimal("310.00"))

    def test_invalid_item_number_shows_error(self):
        result = handle_message(PHONE_1, "99")
        self.assertIn("don't exist", result['text'])

    def test_item_number_zero_invalid(self):
        result = handle_message(PHONE_1, "0")
        self.assertIn("don't exist", result['text'])

    def test_garbage_text_shows_error(self):
        result = handle_message(PHONE_1, "pizza please")
        self.assertIn("didn't understand", result['text'].lower())

    def test_previous_pending_order_replaced(self):
        """Second selection should delete first pending order."""
        handle_message(PHONE_1, "1")
        self.session.state = "show_menu"
        self.session.save()
        handle_message(PHONE_1, "2")
        orders = Order.objects.filter(user=self.session, status='pending')
        self.assertEqual(orders.count(), 1)  # only 1 pending at a time

    def test_unavailable_items_not_in_menu(self):
        make_menu_item("Secret Item", "999.00", available=False)
        result = handle_message(PHONE_1, "menu")
        self.assertNotIn("Secret Item", result['text'])


#  State: confirm_order

class ConfirmOrderTest(TestCase):

    def setUp(self):
        self.session = make_complete_session(PHONE_1)
        self.session.state = "confirm_order"
        self.session.save()
        make_standard_menu()
        self.order = make_order_with_items(self.session)

    def test_confirm_triggers_payment(self):
        with patch('core.payment.create_razorpay_order') as mock_rz, \
            patch('core.payment.get_payment_qr_url', return_value=None), \
            patch('core.payment.get_payment_link', return_value="https://rzp.io/test"):
            mock_rz.return_value = {'id': 'order_test_123'}
            result = handle_message(PHONE_1, "confirm")

        self.assertIn("Payment", result['text'])
        self.session.refresh_from_db()
        self.assertEqual(self.session.state, "awaiting_payment")

    def test_confirm_saves_razorpay_order_id(self):
        with patch('core.payment.create_razorpay_order') as mock_rz, \
            patch('core.payment.get_payment_qr_url', return_value=None), \
            patch('core.payment.get_payment_link', return_value="https://rzp.io/test"):
            mock_rz.return_value = {'id': 'order_RAZORPAY_123'}
            handle_message(PHONE_1, "confirm")

        self.order.refresh_from_db()
        self.assertEqual(self.order.razorpay_order_id, "order_RAZORPAY_123")

    def test_menu_command_goes_back_to_menu(self):
        result = handle_message(PHONE_1, "menu")
        self.assertIn("Our Menu", result['text'])
        self.session.refresh_from_db()
        self.assertEqual(self.session.state, "show_menu")

    def test_random_text_asks_to_confirm(self):
        result = handle_message(PHONE_1, "ok sounds good")
        self.assertIn("confirm", result['text'].lower())
        self.session.refresh_from_db()
        self.assertEqual(self.session.state, "confirm_order")

    def test_razorpay_failure_shows_error(self):
        with patch('core.payment.create_razorpay_order', return_value=None):
            result = handle_message(PHONE_1, "confirm")
        self.assertIn("error", result['text'].lower())
        self.session.refresh_from_db()
        self.assertEqual(self.session.state, "confirm_order")

    def test_payment_link_included_in_response(self):
        with patch('core.payment.create_razorpay_order') as mock_rz, \
            patch('core.payment.get_payment_qr_url', return_value=None), \
            patch('core.payment.get_payment_link', return_value="https://rzp.io/link123"):
            mock_rz.return_value = {'id': 'order_abc'}
            result = handle_message(PHONE_1, "confirm")

        self.assertEqual(result['payment_link'], "https://rzp.io/link123")

    def test_qr_url_in_media_url(self):
        with patch('core.payment.create_razorpay_order') as mock_rz, \
            patch('core.payment.get_payment_qr_url', return_value="https://qr.example.com/img.png"), \
            patch('core.payment.get_payment_link', return_value=None):
            mock_rz.return_value = {'id': 'order_abc'}
            result = handle_message(PHONE_1, "confirm")

        self.assertEqual(result['media_url'], "https://qr.example.com/img.png")


#  State: awaiting_payment

class AwaitingPaymentTest(TestCase):

    def setUp(self):
        self.session = make_complete_session(PHONE_1)
        self.session.state = "awaiting_payment"
        self.session.save()
        self.order = make_order(self.session, razorpay_order_id="order_rz_001")

    def test_message_while_waiting_shows_pending_notice(self):
        result = handle_message(PHONE_1, "have you received payment?")
        self.assertIn("waiting", result['text'].lower())

    def test_already_paid_order_gives_friendly_message(self):
        self.order.status = "paid"
        self.order.save()
        result = handle_message(PHONE_1, "hello?")
        self.assertIn("confirmed", result['text'].lower())


#  State: completed

class CompletedStateTest(TestCase):

    def setUp(self):
        self.session = make_complete_session(PHONE_1)
        self.session.state = "completed"
        self.session.save()

    def test_completed_message_shown(self):
        result = handle_message(PHONE_1, "thanks")
        self.assertIn("completed", result['text'].lower())

    def test_hi_after_completed_restarts(self):
        result = handle_message(PHONE_1, "hi")
        self.assertIn("first name", result['text'].lower())
        self.session.refresh_from_db()
        self.assertEqual(self.session.state, "ask_firstname")


#  Cancel command (works from any state)

class CancelCommandTest(TestCase):

    def test_cancel_from_new_state(self):
        result = handle_message(PHONE_1, "cancel")
        self.assertIn("cancelled", result['text'].lower())

    def test_cancel_resets_state_to_new(self):
        make_session(PHONE_1, state="confirm_order")
        handle_message(PHONE_1, "cancel")
        session = UserSession.objects.get(phone=PHONE_1)
        self.assertEqual(session.state, "new")

    def test_cancel_cancels_pending_orders(self):
        session = make_complete_session(PHONE_1)
        session.state = "confirm_order"
        session.save()
        make_order(session, status="pending")
        handle_message(PHONE_1, "cancel")
        self.assertEqual(Order.objects.filter(user=session, status="pending").count(), 0)
        self.assertEqual(Order.objects.filter(user=session, status="cancelled").count(), 1)

    def test_cancel_case_insensitive(self):
        handle_message(PHONE_1, "CANCEL")
        session = UserSession.objects.get(phone=PHONE_1)
        self.assertEqual(session.state, "new")


#  Multiple users (isolation)

class MultipleUsersTest(TestCase):

    def test_two_users_independent_sessions(self):
        """Each phone number has its own session."""
        handle_message(PHONE_1, "hi")
        handle_message(PHONE_2, "hi")
        handle_message(PHONE_1, "Vivek")   # user1 enters first name
        # user2 should still be in ask_firstname
        session2 = UserSession.objects.get(phone=PHONE_2)
        self.assertEqual(session2.state, "ask_firstname")
        session1 = UserSession.objects.get(phone=PHONE_1)
        self.assertEqual(session1.state, "ask_lastname")

    def test_two_users_independent_orders(self):
        make_standard_menu()
        s1 = make_complete_session(PHONE_1)
        s2 = make_complete_session(PHONE_2)
        handle_message(PHONE_1, "1")
        handle_message(PHONE_2, "2")
        self.assertEqual(Order.objects.filter(user=s1).count(), 1)
        self.assertEqual(Order.objects.filter(user=s2).count(), 1)
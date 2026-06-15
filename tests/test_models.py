"""
Unit tests for UserSession, MenuItem, Order, OrderItem models.

"""

from decimal import Decimal
from django.test import TestCase
from core.models import UserSession, MenuItem, Order, OrderItem
from .factories import (
    make_menu_item, make_standard_menu,
    make_session, make_complete_session,
    make_order, make_order_with_items,
    PHONE_1, PHONE_2,
)

#  UserSession model

class UserSessionModelTest(TestCase):

    def test_create_session_defaults(self):
        """New session should start in 'new' state with blank profile."""
        session = UserSession.objects.create(phone=PHONE_1)
        self.assertEqual(session.state, "new")
        self.assertEqual(session.first_name, "")
        self.assertEqual(session.last_name, "")
        self.assertEqual(session.address, "")
        self.assertEqual(session.contact_phone, "")

    def test_full_name_property(self):
        session = UserSession.objects.create(
            phone=PHONE_1, first_name="Vivek", last_name="Sharma"
        )
        self.assertEqual(session.full_name, "Vivek Sharma")

    def test_full_name_only_first_name(self):
        """full_name should not have trailing space when last_name is blank."""
        session = UserSession.objects.create(phone=PHONE_1, first_name="Vivek")
        self.assertEqual(session.full_name, "Vivek")

    def test_full_name_blank(self):
        session = UserSession.objects.create(phone=PHONE_1)
        self.assertEqual(session.full_name, "")

    def test_str_representation(self):
        session = UserSession.objects.create(
            phone=PHONE_1, first_name="Vivek", last_name="Sharma"
        )
        self.assertIn("Vivek", str(session))
        self.assertIn(PHONE_1, str(session))

    def test_phone_is_unique(self):
        """Duplicate phone should raise IntegrityError."""
        UserSession.objects.create(phone=PHONE_1)
        with self.assertRaises(Exception):
            UserSession.objects.create(phone=PHONE_1)

    def test_state_transitions_are_valid(self):
        """All expected states should be storable."""
        valid_states = [
            'new', 'ask_firstname', 'ask_lastname', 'ask_address',
            'ask_phone', 'show_menu', 'awaiting_order',
            'confirm_order', 'awaiting_payment', 'completed',
        ]
        session = UserSession.objects.create(phone=PHONE_1)
        for state in valid_states:
            session.state = state
            session.save()
            session.refresh_from_db()
            self.assertEqual(session.state, state)

#  MenuItem model

class MenuItemModelTest(TestCase):

    def test_create_menu_item(self):
        item = make_menu_item("Burger", "120.00", "🍔")
        self.assertEqual(item.name, "Burger")
        self.assertEqual(item.price, Decimal("120.00"))
        self.assertTrue(item.is_available)

    def test_str_representation(self):
        item = make_menu_item("Burger", "120.00")
        self.assertIn("Burger", str(item))
        self.assertIn("120", str(item))

    def test_unavailable_item(self):
        item = make_menu_item("Old Item", "50.00", available=False)
        self.assertFalse(item.is_available)

    def test_default_emoji(self):
        item = MenuItem.objects.create(name="Test", price=Decimal("10.00"))
        self.assertEqual(item.emoji, "🍽️")

#  Order + OrderItem models

class OrderModelTest(TestCase):

    def setUp(self):
        self.session = make_complete_session()
        self.burger, self.pizza, self.fries = make_standard_menu()

    def test_order_has_uuid(self):
        order = Order.objects.create(user=self.session)
        self.assertIsNotNone(order.order_id)

    def test_order_default_status_is_pending(self):
        order = Order.objects.create(user=self.session)
        self.assertEqual(order.status, "pending")

    def test_calculate_total_single_item(self):
        order = Order.objects.create(user=self.session)
        OrderItem.objects.create(order=order, item=self.burger, quantity=1)
        total = order.calculate_total()
        self.assertEqual(total, Decimal("120.00"))
        self.assertEqual(order.total_amount, Decimal("120.00"))

    def test_calculate_total_multiple_items(self):
        order = Order.objects.create(user=self.session)
        OrderItem.objects.create(order=order, item=self.burger, quantity=2)  # 240
        OrderItem.objects.create(order=order, item=self.pizza,  quantity=1)  # 250
        total = order.calculate_total()
        self.assertEqual(total, Decimal("490.00"))

    def test_calculate_total_with_quantity(self):
        order = Order.objects.create(user=self.session)
        OrderItem.objects.create(order=order, item=self.fries, quantity=3)  # 3 * 70 = 210
        total = order.calculate_total()
        self.assertEqual(total, Decimal("210.00"))

    def test_order_item_subtotal(self):
        order = Order.objects.create(user=self.session)
        oi = OrderItem.objects.create(order=order, item=self.pizza, quantity=2)
        self.assertEqual(oi.subtotal, Decimal("500.00"))  # 250 * 2

    def test_order_str(self):
        order = make_order(self.session)
        self.assertIn("120", str(order))

    def test_order_item_str(self):
        order = Order.objects.create(user=self.session)
        oi = OrderItem.objects.create(order=order, item=self.burger, quantity=2)
        self.assertIn("2", str(oi))
        self.assertIn("Chicken Burger", str(oi))

    def test_order_cascade_delete(self):
        """Deleting an order should also delete its items."""
        order = make_order_with_items(self.session)
        order_id = order.pk
        order.delete()
        self.assertEqual(OrderItem.objects.filter(order_id=order_id).count(), 0)

    def test_multiple_orders_per_user(self):
        order1 = make_order(self.session)
        order2 = make_order(self.session)
        self.assertEqual(self.session.orders.count(), 2)
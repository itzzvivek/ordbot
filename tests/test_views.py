"""
Tests for WhatsApp webhook and Razorpay payment webhook views.
"""

import json
import hmac
import hashlib
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.urls import reverse

from core.models import UserSession, Order, OrderItem
from .factories import (
    make_complete_session, make_order, make_order_with_items,
    make_standard_menu, twilio_post,
    razorpay_payment_captured_payload, razorpay_payment_failed_payload,
    PHONE_1,
)


def make_razorpay_signature(payload: dict, secret: str = "test_secret") -> str:
    """Generate a valid Razorpay webhook signature for testing."""
    body = json.dumps(payload).encode()
    return hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()

#  WhatsApp Webhook View

class WhatsAppWebhookTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = '/whatsapp/'

    def _post(self, body, phone=PHONE_1):
        return self.client.post(self.url, twilio_post(body, phone),
                                content_type='application/x-www-form-urlencoded')

    def test_webhook_returns_200(self):
        resp = self._post("hi")
        self.assertEqual(resp.status_code, 200)

    def test_webhook_returns_xml(self):
        resp = self._post("hi")
        self.assertIn('text/xml', resp['Content-Type'])

    def test_hi_triggers_welcome(self):
        resp = self._post("hi")
        self.assertIn(b'Welcome', resp.content)

    def test_response_contains_twiml_message_tag(self):
        resp = self._post("hi")
        self.assertIn(b'<Message>', resp.content)

    def test_missing_body_handled_gracefully(self):
        resp = self.client.post(self.url, {'From': PHONE_1, 'NumMedia': '0'},
                                content_type='application/x-www-form-urlencoded')
        self.assertEqual(resp.status_code, 200)

    def test_missing_from_returns_200(self):
        resp = self.client.post(self.url, {'Body': 'hi', 'NumMedia': '0'},
                                content_type='application/x-www-form-urlencoded')
        self.assertEqual(resp.status_code, 200)

    def test_media_message_handled(self):
        """User sends an image — should not crash."""
        resp = self.client.post(self.url, {
            'Body': '', 'From': PHONE_1,
            'NumMedia': '1', 'MediaUrl0': 'https://example.com/img.jpg'
        }, content_type='application/x-www-form-urlencoded')
        self.assertEqual(resp.status_code, 200)

    def test_full_flow_name_collection(self):
        """Walk through hi → first name → last name."""
        self._post("hi")
        self._post("Vivek")
        resp = self._post("Sharma")
        self.assertIn(b'address', resp.content.lower())

    def test_full_flow_to_menu(self):
        """Walk through entire profile collection to see menu."""
        make_standard_menu()
        self._post("hi")
        self._post("Vivek")
        self._post("Sharma")
        self._post("123 MG Road Indore")
        resp = self._post("9876543210")
        self.assertIn(b'Menu', resp.content)

    def test_cancel_resets_session(self):
        make_complete_session(PHONE_1)
        self._post("cancel")
        session = UserSession.objects.get(phone=PHONE_1)
        self.assertEqual(session.state, 'new')
        self.assertEqual(session.first_name, '')

#  Razorpay Payment Webhook View

class RazorpayWebhookTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = '/payment/webhook/'
        self.secret = 'test_secret'
        self.session = make_complete_session(PHONE_1)
        make_standard_menu()
        self.order = make_order(
            self.session,
            status='pending',
            razorpay_order_id='order_test_123'
        )

    def _post_webhook(self, payload: dict, secret: str = None):
        body = json.dumps(payload).encode()
        sig = hmac.new(
            (secret or self.secret).encode(),
            body, hashlib.sha256
        ).hexdigest()
        return self.client.post(
            self.url,
            data=body,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )

    def test_invalid_signature_returns_400(self):
        payload = razorpay_payment_captured_payload('order_test_123')
        resp = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='invalidsignature',
        )
        self.assertEqual(resp.status_code, 400)

    def test_invalid_json_returns_400(self):
        body = b'not-json'
        sig = hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()
        resp = self.client.post(
            self.url, data=body,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        self.assertEqual(resp.status_code, 400)

    def test_unknown_event_returns_ignored(self):
        payload = {'event': 'some.unknown.event', 'payload': {}}
        resp = self._post_webhook(payload)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'ignored', resp.content)

    @patch('core.views._send_success_whatsapp')
    def test_payment_captured_marks_order_paid(self, mock_send):
        payload = razorpay_payment_captured_payload('order_test_123', 'pay_abc')
        with self.settings(RAZORPAY_WEBHOOK_SECRET=self.secret):
            resp = self._post_webhook(payload)
        self.assertEqual(resp.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'paid')
        self.assertEqual(self.order.payment_id, 'pay_abc')

    @patch('core.views._send_success_whatsapp')
    def test_payment_captured_updates_session_state(self, mock_send):
        payload = razorpay_payment_captured_payload('order_test_123')
        with self.settings(RAZORPAY_WEBHOOK_SECRET=self.secret):
            self._post_webhook(payload)
        self.session.refresh_from_db()
        self.assertEqual(self.session.state, 'completed')

    @patch('core.views._send_success_whatsapp')
    def test_payment_captured_calls_whatsapp_send(self, mock_send):
        payload = razorpay_payment_captured_payload('order_test_123')
        with self.settings(RAZORPAY_WEBHOOK_SECRET=self.secret):
            self._post_webhook(payload)
        mock_send.assert_called_once_with(self.order)

    @patch('core.views._send_success_whatsapp')
    def test_payment_captured_idempotent(self, mock_send):
        """Sending same webhook twice should not process twice."""
        self.order.status = 'paid'
        self.order.save()
        payload = razorpay_payment_captured_payload('order_test_123')
        with self.settings(RAZORPAY_WEBHOOK_SECRET=self.secret):
            resp = self._post_webhook(payload)
        data = json.loads(resp.content)
        self.assertEqual(data['status'], 'already processed')
        mock_send.assert_not_called()

    def test_payment_captured_order_not_found_returns_404(self):
        payload = razorpay_payment_captured_payload('order_NONEXISTENT')
        with self.settings(RAZORPAY_WEBHOOK_SECRET=self.secret):
            resp = self._post_webhook(payload)
        self.assertEqual(resp.status_code, 404)

    @patch('core.views._send_payment_failed_whatsapp')
    def test_payment_failed_calls_failed_whatsapp(self, mock_send):
        payload = razorpay_payment_failed_payload('order_test_123')
        with self.settings(RAZORPAY_WEBHOOK_SECRET=self.secret):
            resp = self._post_webhook(payload)
        self.assertEqual(resp.status_code, 200)
        mock_send.assert_called_once()

    @patch('core.views._send_payment_failed_whatsapp')
    def test_payment_failed_nonexistent_order_no_crash(self, mock_send):
        payload = razorpay_payment_failed_payload('order_NONEXISTENT')
        with self.settings(RAZORPAY_WEBHOOK_SECRET=self.secret):
            resp = self._post_webhook(payload)
        self.assertEqual(resp.status_code, 200)
        mock_send.assert_not_called()


#  Payment Callback View

class PaymentCallbackTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = '/payment/callback/'

    def test_paid_status_shows_success(self):
        resp = self.client.get(self.url, {
            'razorpay_payment_id': 'pay_test123',
            'razorpay_payment_link_status': 'paid',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Payment Successful', resp.content)

    def test_unpaid_status_shows_incomplete(self):
        resp = self.client.get(self.url, {
            'razorpay_payment_link_status': 'created',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Incomplete', resp.content)

    def test_missing_status_shows_incomplete(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Incomplete', resp.content)
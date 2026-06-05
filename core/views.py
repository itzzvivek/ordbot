"""
Endpoints:
    POST /whatsapp/ -> Twilio Whatsapp webhook
    POST /payment/webhook/ -> Razorpay payment webhook
    GET /payment/callback/ -> Razorpay  redirect after payment 
"""

import json
import logging

from django.http import HttpResponse, JsonResponse
from django.views.decoreators.csrf import csrf_exempt
from django.views.decoreators.https import require_POST, require_GET
from twilio.twiml.messaging_response import MessagingResponse

from .bot import handle_message
from .models import UserSession, Order
from .payment import verify_webhook_signature

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def whatsapp_webhook(request):
    """
    Twilio calls this endpoint whenever a Whatsapp message arrives.
    We respond with TwiML to send a reply message back to the user.
    """
    incoming_msg = request.POST.get('Body', '').strip()
    sender       = request.POST.get('From', '').strip()   # e.g. whatsapp:+919876543210
    num_media    = int(request.POST.get('NumMedia', 0))

    logger.info(f"Incoming from {sender}: {incoming_msg!r}")

    resp = MessagingResponse()

    if not sender:
        return HttpResponse(str(resp), content_type='text/xml')

    # If user sent a media file (e.g. payment screenshot) — ignore gracefully
    if num_media > 0 and not incoming_msg:
        incoming_msg = '[media]'

    try:
        result = handle_message(sender, incoming_msg)
    except Exception as e:
        logger.exception(f"Bot error for {sender}: {e}")
        result = {'text': '⚠️ Something went wrong. Please try again.', 'media_url': None}

    msg = resp.message(result['text'])

    # Attach QR code image if provided
    if result.get('media_url'):
        msg.media(result['media_url'])

    return HttpResponse(str(resp), content_type='text/xml')


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    """
    Razorpay sends a POST to this endpoint when a payment event occurs.
    We verify the signature, mark the order paid, and send a WhatsApp
    success message to the customer.
    """

    payload_body = request.body
    signature = request.headers.get('X-Razorpay-Signature', '')

    # verify signature
    if not verify_webhook_signature(payload_body, signature):
        logger.warning("Razorpay webhook signature verification failed")
        return HttpResponse({"error": "Invalid signature"}, status=400)
    
    # parse event
    try:
        event = json.loads(payload_body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    event_type = event.get('event')
    logger.info(f"Razorpay webhook received: {event_type}")

    # Handle payment.captured (order is paid)
    if event_type == "payment.captured":
        payment = event['payload']['payment']['entity']
        payment_id = payment.get['id']
        rz_order_id = payment.get['order_id']
        notes = payment.get('notes', {})
        order_uuid = notes.get('order_uuid')

        try:
            order = Order.objects.get(order_id=order_uuid)
        except Order.DoesNotExist:
            logger.error(f"Order not found for Razorpay order_id: {rz_order_id}")
            return JsonResponse({"error": "Order not found"}, status=404)
        
        if order.status != 'paid':
            return JsonResponse({'status': 'already processed'})

        # mark paid
        order.payment_id = payment_id
        order.status = 'paid'
        order.save()

        # update user session state
        session = order.user
        session.state = 'completed'
        session.save()


        # send whatsapp success message
        _send_success_whatapp(order)

        logger.info(f"Order {order.order_id} marked as paid and Payment ID {payment_id}")
        return JsonResponse({"status": "success"})

        # Handle payment. failed

    elif event_type == "payment.failed":
        payment = event['payload']['payment']['entity']
        rz_order_id = payment.get('order_id')
        
        try:
            order = Order.objects.get(razorpay_order_id=rz_order_id)
            _send_payment_failed_whatsapp(order)
        except Order.DoesNotExist:
            pass

        return JsonResponse({"status": "noted"})
    return JsonResponse({"status": "ignored"})

#  Razorpay Redirect Callback (browser redirect after payment)

@require_GET
def payment_callback(request):
    """
    Razorpay redirects the user's browser here after payment.
    This is a simple acknowledgment page.
    """
    razorpay_payment_id = request.GET.get('razorpay_payment_id', '')
    status = request.GET.get('razorpay_payment_link_status', '')

    if status == 'paid':
        html = """
        <html><body style="font-family:sans-serif;text-align:center;padding:40px;">
        <h1>✅ Payment Successful!</h1>
        <p>Thank you! Your order is confirmed.</p>
        <p>You'll receive a WhatsApp confirmation shortly. 🎉</p>
        </body></html>
        """
    else:
        html = """
        <html><body style="font-family:sans-serif;text-align:center;padding:40px;">
        <h1>⚠️ Payment Incomplete</h1>
        <p>Your payment was not completed.</p>
        <p>Please return to WhatsApp and type <b>confirm</b> to retry.</p>
        </body></html>
        """
    return HttpResponse(html)

    
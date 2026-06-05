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

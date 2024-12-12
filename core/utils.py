from ctypes.wintypes import PSIZE
from http.client import responses

from django.conf import settings
from twilio.rest import Client
import requests

def send_whatsapp_message(to, body):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        body=body,
        from_=settings.TWILIO_WHATSAPP_NUMBER_FROM,
        to=f'whatsapp:{to}'
    )
    return message.sid


def send_subscription_options(phone_number):
    """
    Sends subscription options as an interaction message via twilio api
    """

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    body = (
        "Subscription Options:\n"
        "1. Monthly Plan - $10/month (Reply with 'monthly')\n"
        "2. Quarterly Plan - $25/3 months (Reply with 'quarterly')\n"
        "3. Yearly Plan - $90/year (Reply with 'yearly')"
    )
    client.messages.create(
        body=body,
        from_=f'whatsapp:{settings.TWILIO_WHATSAPP_NUMBER_FROM}',
        to=f'whatsapp:{phone_number}'
    )
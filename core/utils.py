import logging
import re

from django.conf import settings
from twilio.rest import Client
from requests.auth import HTTPBasicAuth
import requests

logger = logging.getLogger(__name__)

def send_whatsapp_message(phone_number, body):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        body=body,
        from_=settings.TWILIO_WHATSAPP_NUMBER_FROM,
        to=f'whatsapp:{phone_number}'
    )
    return message.sid


def validate_phone_number(phone_number):
    """
    validates phone number formate to ensure it matches international standards.
    """
    pattern = re.compile(r"^\+?\d{10,15}$")
    if not pattern.match(phone_number):
        raise ValueError(f"Invalid phone number: {phone_number}")
    return phone_number


def send_interactive_message(phone_number, body, buttons):
    """
    Sends an interactive WhatsApp message with buttons.
    """
    try:
        # Validate phone number
        validate_phone_number(phone_number)

        # Twilio API URL
        url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
        auth = HTTPBasicAuth(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        # Create payload
        payload = {
            "To": f"whatsapp:{phone_number}",
            "From": settings.TWILIO_WHATSAPP_NUMBER_FROM,
            "Interactive": {
                "type": "button",
                "header": {"type": "text", "text": body},
                "body": {"text": body},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": btn["payload"], "title": btn["title"]}}
                        for btn in buttons
                    ]
                },
            },
        }

        # Send request
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, auth=auth)

        # Check response
        if response.status_code == 201:
            sid = response.json().get('sid')
            logger.info(f"Interactive message sent successfully to {phone_number}. SID: {sid}")
            return sid
        else:
            logger.error(f"Failed to send interactive message: {response.status_code} - {response.text}")
            response.raise_for_status()
    except Exception as e:
        logger.error(f"Error sending interactive message: {e}")
        raise



def send_subscription_options(phone_number):
    """
    Sends subscription options as an interaction message via twilio api
    """

    # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    # body = (
    #     "Subscription Options:\n"
    #     "1. Monthly Plan - $10/month (Reply with 'monthly')\n"
    #     "2. Quarterly Plan - $25/3 months (Reply with 'quarterly')\n"
    #     "3. Yearly Plan - $90/year (Reply with 'yearly')"
    # )
    # client.messages.create(
    #     body=body,
    #     from_=settings.TWILIO_WHATSAPP_NUMBER_FROM,
    #     to=settings.TWILIO_WHATSAPP_NUMBER_TO,
    # )

    buttons = [
        {"type": "reply", "title": "Monthly Plan", "payload": "monthly"},
        {"type": "reply", "title": "Quarterly Plan", "payload": "quarterly"},
        {"type": "reply", "title": "Yearly Plan", "payload": "yearly"}
    ]
    message = "Please choose a subscription plan:"
    send_interactive_message(phone_number, message, buttons)

from http.client import responses
from django.conf import settings
from twilio.rest import Client
from requests.auth import HTTPBasicAuth
import requests


def send_whatsapp_message(to, body):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    print(f"SID: {settings.TWILIO_ACCOUNT_SID}")
    print(f"token: {settings.TWILIO_AUTH_TOKEN}")
    message = client.messages.create(
        body=body,
        from_=settings.TWILIO_WHATSAPP_NUMBER_FROM,
        to=f'whatsapp:{to}'
    )
    return message.sid


def send_interactive_message(phone_number, body, buttons):
    """
    Sends an interactive WhatsApp message with buttons.
    """

    # Ensure that the phone number is prefixed with 'whatsapp:' and properly formatted
    to_number = f"whatsapp:{phone_number}"
    print(f"To Number: {to_number}")  # Debugging to check the formatted phone number

    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
    print(f"URL: {url}")  # Debugging the URL

    # Use HTTPBasicAuth to handle authentication with SID and Auth Token
    auth = HTTPBasicAuth(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    # Prepare the payload for the interactive message
    payload = {
        "to": to_number,  # The recipient phone number with 'whatsapp:' prefix
        "from": settings.TWILIO_WHATSAPP_NUMBER_FROM,  # Your Twilio WhatsApp number
        "interactive": {
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

    # Send the POST request to Twilio API
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, auth=auth)

    # Handle the response
    if response.status_code != 200:
        print(f"Error sending message: {response.text}")
    else:
        print(f"Message sent successfully with SID: {response.json().get('sid')}")

    return response


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

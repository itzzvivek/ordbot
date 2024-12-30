from http.client import responses
from django.conf import settings
from twilio.rest import Client
from requests.auth import HTTPBasicAuth
import requests


def send_whatsapp_message(phone_number, body):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        body=body,
        from_=settings.TWILIO_WHATSAPP_NUMBER_FROM,
        to=f'whatsapp:{phone_number}'
    )
    print(f"phone_number: {phone_number}")
    return message.sid


def send_interactive_message(phone_number, buttons, template_name, parameters):
    """
    Sends an interactive WhatsApp message with buttons via Twilio API.
    """
    if not phone_number:
        print("Error: Phone number is missing")
        return {"error": "Phone number is missing"}

    # Twilio API URL
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"

    # Twilio Authentication
    auth = HTTPBasicAuth(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


    # Format payload for Twilio
    payload = {
        "To": f"whatsapp:{phone_number}",
        "From": settings.TWILIO_WHATSAPP_NUMBER_FROM,
        # "Body": body,  # Add the message body text
        "TemplateName": template_name,
        "template_language_code": "en",
        "template_buttons": parameters,
        "interactive_buttons": buttons
    }

    # Send the request to Twilio
    response = requests.post(
        url, json=payload, headers={"Content-Type": "application/json"}, auth=auth
    )

    # Handle response
    if response.status_code != 201:
        print(f"Error sending message: {response.status_code} - {response.text}")
        return {"error": response.json()}
    else:
        print(f"Message sent successfully with SID: {response.json().get('sid')}")
        return {"sid": response.json().get("sid")}


def send_subscription_options(phone_number):
    """
    Sends subscription options as an interaction message via twilio api
    """

    buttons = [
        {"type": "reply", "title": "Monthly Plan", "payload": "monthly"},
        {"type": "reply", "title": "Quarterly Plan", "payload": "quarterly"},
        {"type": "reply", "title": "Yearly Plan", "payload": "yearly"}
    ]
    message = "Please choose a subscription plan:"
    send_interactive_message(phone_number, message, buttons)

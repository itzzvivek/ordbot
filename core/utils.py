from ctypes.wintypes import PSIZE

from django.conf import settings
from twilio.rest import Client


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
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token = settings.TWILIO_AUTH_TOKEN
    client = Client(account_sid, auth_token)

    from_number = 'whatsapp:TWILIO_WHATSAPP_NUMBER_FROM'
    to_number = 'whatsapp:TWILIO_WHATSAPP_NUMBER_TO'

    # Interactive list message payload

    message = client.messages.create(
        from_=from_number,
        to=to_number,
        interactive={
            "type": "list",
            "header": {
                "type": "text",
                "text": "Subscription Options"
            },
            "body": {
                "text": "Please select your subscription plan:"
            },
            "footer": {
                "text": "Tap an option to choose your subscription."
            },
            "action": {
                "button": "Choose Plan",
                "sections": [
                    {
                        "title": "Available Plans",
                        "rows": [
                            {"id": "monthly_subscription", "title": "Monthly", "description": "$10 per month"},
                            {"id": "quarterly_subscription", "title": "Quarterly", "description": "$25 per 3 months"},
                            {"id": "yearly_subscription", "title": "Yearly", "description": "$90 per year"}
                        ]
                    }
                ]
            }
        }
    )

    print(f"Message SID: {message.sid}")
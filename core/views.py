from http.client import responses

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt

from .utils import send_whatsapp_message, send_subscription_options
from .models import Client


@csrf_exempt
@api_view(['POST'])
def handle_whatsapp_message(request):
    print("Incoming request data:", request.data)
    phone_number = request.data.get('From', '').replace('whatsapp:', '')
    message_body = request.data.get('Body', '').strip().lower()

    registration_stage = request.session.get('registration_stage')
    print(f"register stage: {registration_stage}")

    if registration_stage is None and message_body == 'register-client':
        # start registration process
        request.session['registration_stage'] = 'first_name'
        send_whatsapp_message(phone_number, "Please Enter your first name.")
        return Response({'status': 'success', 'message': 'Asking for first name'})

    if registration_stage == 'first_name':
        request.session['first_name'] = message_body
        request.session['registration_stage'] = 'last_name'
        send_whatsapp_message(phone_number, "Please Enter your last name.")
        return Response({'status': 'success', 'message': 'Asking for last name'})

    if registration_stage == 'last_name':
        request.session['last_name'] = message_body
        request.session['registration_stage'] = 'phone_number'
        send_whatsapp_message(phone_number, "Please Enter your phone_number")
        return Response({'status': 'success', 'message': 'Asking for phone number'})

    if registration_stage == 'phone_number':
        # Validate the phone number format
        if message_body.isdigit() and len(message_body) == 10:
            # Save the phone number and proceed to subscription stage
            request.session['phone_number'] = message_body
            request.session['registration_stage'] = 'subscription'
            send_subscription_options(phone_number)  # Function to send subscription options
            return Response({'status': 'success', 'message': 'Subscription options sent'})
        else:
            # Handle invalid phone number
            send_whatsapp_message(
                phone_number,
                "Invalid phone number. Please enter a valid phone number."
            )
            return Response({'status': 'error', 'message': 'Invalid phone number'})

    if registration_stage == 'subscription':
        valid_choices = ['monthly_subscription', 'quarterly_subscription', 'yearly_subscription']
        if message_body in valid_choices:
            subscription_plan = message_body.replace('_', ' ').capitalize()
            request.session['subscription_choice'] = subscription_plan
            send_whatsapp_message(phone_number, f"Thank you for selecting the {subscription_plan} plan!")

            # Retrieve stored user details
            first_name = request.session.get('first_name')
            last_name = request.session.get('last_name')
            phone = request.session.get('phone_number')

            # Save client data
            Client.objects.create(
                phone_number=phone,
                first_name=first_name,
                last_name=last_name,
                subscription_plan=subscription_plan
            )

            # Clear session after registration
            request.session.flush()

            # Send confirmation message
            send_whatsapp_message(
                phone_number,
                f"Thank you {first_name} {last_name}! Your phone number {phone} has been registered with the {subscription_plan} plan."
            )
            return Response({'status': 'success', 'message': 'Registration complete'})
        else:
            # Handle invalid subscription choice
            send_whatsapp_message(phone_number, "Invalid choice. Please select a valid subscription option.")
            return Response({'status': 'error', 'message': 'Invalid subscription choice'})

    send_whatsapp_message(phone_number, "Invalid command or stage. Please type valid command")
    return Response({'status': 'error', 'message': 'Invalid command or stage'})



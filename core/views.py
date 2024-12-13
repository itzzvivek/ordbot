from http.client import responses
from multiprocessing.resource_tracker import register

from django.core.mail.message import sanitize_address
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta

from .utils import send_whatsapp_message, send_subscription_options, send_command_buttons
from .models import Client

import re

SESSION_TIMEOUT_SECONDS = 300

@csrf_exempt
@api_view(['POST'])
def handle_whatsapp_message(request):
    from datetime import datetime, timedelta

    phone_number = request.data.get('From', '').replace('whatsapp:', '')
    message_body = request.data.get('Body', '').strip().lower()

    # Initialize session data
    session_data = request.session.setdefault('registration_data', {})
    registration_stage = session_data.get('stage')
    stage_start_time = session_data.get('stage_start_time')  # Timestamp when stage started

    # Check for session timeout
    if stage_start_time:
        stage_start_time = datetime.fromisoformat(stage_start_time)
        if datetime.now() > stage_start_time + timedelta(seconds=SESSION_TIMEOUT_SECONDS):
            # Session expired
            request.session.flush()  # Clear session
            send_whatsapp_message(phone_number, "Session expired. Please restart by typing 'register-client'.")
            return Response({'status': 'error', 'message': 'Session expired.'})

    # Registration process logic
    if not registration_stage and message_body == 'register-client':
        # Start registration
        session_data['stage'] = 'first_name'
        session_data['stage_start_time'] = datetime.now().isoformat()  # Save stage start time
        request.session.modified = True
        send_whatsapp_message(phone_number, "Please enter your first name.")
        return Response({'status': 'success', 'message': 'First name requested.'})

    if registration_stage == 'first_name':
        session_data['first_name'] = message_body
        session_data['stage'] = 'last_name'
        session_data['stage_start_time'] = datetime.now().isoformat()  # Update stage start time
        request.session.modified = True
        send_whatsapp_message(phone_number, "Please enter your last name.")
        return Response({'status': 'success', 'message': 'Last name requested.'})

    if registration_stage == 'last_name':
        session_data['last_name'] = message_body
        session_data['stage'] = 'phone_number'
        session_data['stage_start_time'] = datetime.now().isoformat()  # Update stage start time
        request.session.modified = True
        send_whatsapp_message(phone_number, "Please enter your phone number.")
        return Response({'status': 'success', 'message': 'Phone number requested.'})

    if registration_stage == 'phone_number':
        sanitized_number = message_body.strip().replace(" ", "").replace("-", "")

        #Add country code if missing
        if not sanitized_number.startswith("+"):
            sanitized_number = f"+91{sanitized_number}"
        # Validate phone number
        phone_number_pattern = re.compile(r"^\+?\d{10,15}$")
        if phone_number_pattern.match(sanitized_number):
            # Check for duplicates
            if Client.objects.filter(phone_number=sanitized_number).exists():
                send_whatsapp_message(phone_number, "This phone number is already registered.")
                return Response({'status': 'error', 'message': 'Duplicate phone number'})

            # Save valid number
            request.session['phone_number'] = sanitized_number
            print(sanitized_number)
            request.session['registration_stage'] = 'subscription'
            send_subscription_options(sanitized_number)
            return Response({'status': 'success', 'message': 'Subscription options sent'})
        else:
            # Handle invalid number
            send_whatsapp_message(phone_number, "Invalid phone number. Please enter a valid number.")
            return Response({'status': 'error', 'message': 'Invalid phone number'})

    if registration_stage == 'subscription':
        valid_choices = ['monthly', 'quarterly', 'yearly']
        if message_body in valid_choices:
            subscription_plan = message_body.capitalize()
            send_whatsapp_message(phone_number, f"Thank you for selecting the {subscription_plan} plan!")

            # Save client data to the database
            Client.objects.create(
                first_name=session_data.get('first_name'),
                last_name=session_data.get('last_name'),
                phone_number=session_data.get('phone_number'),
                membership_type=message_body
            )

            # Clear session after successful registration
            request.session.flush()
            send_whatsapp_message(
                phone_number,
                f"Registration complete! Thank you {session_data.get('first_name')} {session_data.get('last_name')}."
            )
            return Response({'status': 'success', 'message': 'Registration complete.'})
        else:
            send_whatsapp_message(phone_number, "Invalid subscription choice. Please try again.")
            return Response({'status': 'error', 'message': 'Invalid subscription choice.'})

    # Handle unknown stages or commands
    send_whatsapp_message(phone_number, "Invalid command. Please type 'register-client' to start.")
    return Response({'status': 'error', 'message': 'Invalid command.'})




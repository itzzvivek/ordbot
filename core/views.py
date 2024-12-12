from http.client import responses
from multiprocessing.resource_tracker import register

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta

from .utils import send_whatsapp_message, send_subscription_options
from .models import Client

SESSION_TIMEOUT_SECONDS = 60

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
        if message_body.isdigit() and len(message_body) == 10:
            session_data['phone_number'] = message_body
            session_data['stage'] = 'subscription'
            session_data['stage_start_time'] = datetime.now().isoformat()  # Update stage start time
            request.session.modified = True
            send_subscription_options(phone_number)  # Send subscription options
            return Response({'status': 'success', 'message': 'Subscription options sent.'})
        else:
            send_whatsapp_message(phone_number, "Invalid phone number. Please try again.")
            return Response({'status': 'error', 'message': 'Invalid phone number.'})

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




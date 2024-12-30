from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta

from .utils import send_whatsapp_message, send_subscription_options, send_interactive_message
from .models import Client
import re

@csrf_exempt
@api_view(['POST'])
def handle_whatsapp_messages(request):
    """
    Handles initial greetings and responds with available commands as buttons
    """
    phone_number = request.data.get('From', '').replace('whatsapp:', '')
    message_body = request.data.get('Body', '').strip().lower()

    greetings = ['hello', 'hii', 'hey', 'hi']

    if message_body in greetings:
        response_message = "Welcome! Choose an action below:"
        buttons = [
            {"type": "reply", "title": "Register Client", "payload": "register-client"},
            {"type": "reply", "title": "help", "payload": "help"}
        ]
        template_name = "fitbot_template"
        parameters = {"body": response_message}
        send_interactive_message(phone_number, template_name, parameters, buttons)
        return Response({'status': 'success', 'message': 'Interactive buttons sent.'})

    # handle buttons action and commands
    elif message_body == "register-client":
        return register_client(request)
    send_whatsapp_message(phone_number, "Unknown commands. Please type 'Hi' to start")
    return Response({'status': 'error', 'message': 'Unknown command'})


@csrf_exempt
@api_view(['POST'])
def register_client(request):
    phone_number = request.data.get('From', '').replace('whatsapp:', '')
    message_body = request.data.get('Body', '').strip().lower()

    # Initialize session data
    session_data = request.session.setdefault('registration_data', {})
    registration_stage = session_data.get('stage')
    stage_start_time = session_data.get('stage_start_time')  # Timestamp when stage started

    # Check for session timeout
    if stage_start_time:
        stage_start_time = datetime.fromisoformat(stage_start_time)
        if datetime.now() > stage_start_time + timedelta(seconds=settings.SESSION_TIMEOUT):
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

        # Add country code if missing
        if not sanitized_number.startswith("+"):
            sanitized_number = f"+91{sanitized_number}"

        # Validate phone number
        phone_number_pattern = re.compile(r"^\+?\d{10,15}$")
        if phone_number_pattern.match(sanitized_number):
            if Client.objects.filter(phone_number=sanitized_number).exists():
                send_whatsapp_message(phone_number, "This phone number is already registered.")
                return Response({'status': 'error', 'message': 'Duplicate phone number'})

            # Save valid number to session
            session_data['phone_number'] = sanitized_number
            session_data['stage'] = 'subscription'
            session_data['stage_start_time'] = datetime.now().isoformat()
            request.session.modified = True

            # Send subscription options
            send_subscription_options(sanitized_number)
            return Response({'status': 'success', 'message': 'Subscription options sent'})
        else:
            send_whatsapp_message(phone_number, "Invalid phone number. Please try again.")
            return Response({'status': 'error', 'message': 'Invalid phone number'})

    if registration_stage == 'subscription':
        valid_choices = ['monthly', 'quarterly', 'yearly']
        if message_body in valid_choices:
            subscription_plan = message_body
            print(f"User selected plan: {subscription_plan}")

            # Validate session data
            registration_data = request.session.get('registration_data', {})

            if not all(key in registration_data for key in ['first_name', 'last_name', 'phone_number']):
                send_whatsapp_message(phone_number, "Session data missing. Please restart the process.")
                return Response({'status': 'error', 'message': 'Session data incomplete.'})

            # Save client data
            try:
                Client.objects.create(
                    first_name=registration_data['first_name'],
                    last_name=registration_data['last_name'],
                    phone_number=registration_data['phone_number'],
                    membership_type=subscription_plan
                )

                # Send confirmation message
                print("Client saved successfully.")

                send_whatsapp_message(
                    registration_data['phone_number'],
                    f"Registration complete! Thank you {registration_data['first_name']} {registration_data['last_name']}."
                )
                request.session.flush()
                return Response({'status': 'success', 'message': 'Registration complete.'})

            except Exception as e:
                print(f"Error saving client: {e}")
                send_whatsapp_message(phone_number, "Error saving data. Please try again.")
                return Response({'status': 'error', 'message': 'Database error.'})

        else:
            send_whatsapp_message(phone_number, "Invalid subscription choice. Please try again.")
            return Response({'status': 'error', 'message': 'Invalid subscription choice.'})

    # Handle unknown stages or commands
    send_whatsapp_message(phone_number, "Invalid command. Please type 'register-client' to start.")
    return Response({'status': 'error', 'message': 'Invalid command.'})









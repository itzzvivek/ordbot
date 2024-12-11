from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt

from .utils import send_whatsapp_message
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
        # save the phone number complete the registration
        if not  message_body.isdigit() or len(message_body) != 10:
            send_whatsapp_message(
                phone_number,
                "invalid phone number, Please enter a valid phone number"
            )
            return Response({'status': 'error', 'message': 'invalid phone number'})
        request.session['phone_number'] = message_body
        request.session['registration_stage'] = None
        first_name = request.session.get('first_name')
        last_name = request.session.get('last_name')
        Client.objects.create(
            phone_number=message_body,
            first_name=first_name,
            last_name=last_name
        )

        #clear the session
        request.session.flush()

        send_whatsapp_message(
            phone_number,
            f"Thank you {first_name} {last_name}! Your phone number {message_body} has been registered."
        )
        return Response({'status': 'success', 'message': 'Registration complete'})

    return Response({'status': 'error', 'message': 'Invalid command or stage.'})





from django.urls import path
from .views import handle_whatsapp_messages

urlpatterns = [
    # path('register-client/', register_client, name='register_client'),
    # path('check-in/', check_in, name='check_in'),
    # path('my-plan/', subscription_status, name='subscription_status'),
    # path('notify-expiring-subscription/', notify_expiring_subscriptions, name='notify_expiring_subscriptions'),
    path('handle_whatsapp_message/', handle_whatsapp_messages, name='handle-messages'),
]
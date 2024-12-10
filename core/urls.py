from django.urls import path
from .views import handle_whatsapp_message

urlpatterns = [
    # path('register-client/', register_client, name='register_client'),
    # path('check-in/', check_in, name='check_in'),
    # path('my-plan/', subscription_status, name='subscription_status'),
    # path('notify-expiring-subscription/', notify_expiring_subscriptions, name='notify_expiring_subscriptions'),
    path('handle-whatsapp-message/', handle_whatsapp_message, name='handle_whatsapp_message'),
]
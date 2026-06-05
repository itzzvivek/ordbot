from django.urls import path
from . import views 

urlpatterns = [
    path('whatsapp/', views.whatsapp_webhook,  name='whatsapp_webhook'),
    path('payment/webhook/', views.razorpay_webhook,  name='razorpay_webhook'),
    path('payment/callback/', views.payment_callback,  name='payment_callback'),
]
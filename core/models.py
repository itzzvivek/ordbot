from django.db import models
import uuid


class UserSession(models.Model):

    STATE_CHOICES = [
        ('new', 'new/Greeting'),
        ('ask_firstname', 'Asking First Name'),
        ('ask_lastname', 'Asking Last Name'),
        ('ask_address', 'Asking Address'),
        ('ask_phone', 'Asking Phone Number'),
        ('ask_menu', 'Asking Menu'),
        ('awaiting_order', 'Awaiting Order Selection'),
        ('confirm_order', 'Confirming Order'),
        ('awaiting_payment', 'Awaiting Payment'),
        ('completed', 'Order Completed'),
    ]

    phone = models.CharField(max_length=30, unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    contact_number = models.CharField(max_length=30, blank=True)
    state = models.CharField(max_length=30, choices=STATE_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    

class MenuItem(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    is_available = models.BooleanField(default=True)
    emoji = models.CharField(max_length=10, default='🍽️')

    def __str__(self):
        return f"{self.name} - ₹{self.price}"

class Order(models.Model):
    STATUS = [
        ('pending',   'Pending'),
        ('paid',      'Paid'),
        ('preparing', 'Preparing'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    order_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(UserSession, on_delete=models.CASCADE, related_name='orders')
    items = models.ManyToManyField(MenuItem, through='OrderItem')
    status = models.ManyToManyField(MenuItem, through='OrderItem')
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # payment details
    payment_id = models.CharField(max_length=100, blank=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{str(self.order_id)[:8]} - {self.user.full_name} - ₹{self.total_amount}"
    
    def calculate_total(self):
        from decimal import Decimal
        total = Decimal('0.00')
        for oi in self.orderitem_set.select_related('item').all():
            total += oi.item.price * oi.quantity
        self.total_amount = total
        self.save()
        return total
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def subtotal(self):
        return self.item.price * self.quantity
    
    def __str__(self):
        return f"{self.quantity} x {self.item.name}"
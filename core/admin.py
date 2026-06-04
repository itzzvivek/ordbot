from django.contrib import admin
from .models import UserSession, MenuItem, Order, OrderItem


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display  = ('name', 'price', 'emoji', 'is_available')
    list_editable = ('price', 'is_available')
    search_fields = ('name',)


class OrderItemInline(admin.TabularInline):
    model  = OrderItem
    extra  = 0
    readonly_fields = ('subtotal',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ('short_id', 'user', 'total_amount', 'status', 'created_at')
    list_filter   = ('status',)
    search_fields = ('order_id', 'user__first_name', 'user__last_name', 'user__phone')
    readonly_fields = ('order_id', 'razorpay_order_id', 'payment_id', 'total_amount', 'created_at')
    inlines       = [OrderItemInline]

    def short_id(self, obj):
        return str(obj.order_id)[:8].upper()
    short_id.short_description = 'Order ID'


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display  = ('full_name', 'phone', 'state', 'updated_at')
    list_filter   = ('state',)
    search_fields = ('first_name', 'last_name', 'phone')
    readonly_fields = ('created_at', 'updated_at')
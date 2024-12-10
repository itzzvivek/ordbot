from django.contrib import admin
from .models import GymOwner, Client, Attendance, Subscription


class ClientAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'membership_type')


admin.site.register(GymOwner)
admin.site.register(Client, ClientAdmin)
admin.site.register(Attendance)
admin.site.register(Subscription)

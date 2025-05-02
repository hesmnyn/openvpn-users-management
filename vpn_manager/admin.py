from django.contrib import admin
from .models import VPNUser

@admin.register(VPNUser)
class VPNUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'expiry_date', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('username',)
    ordering = ('username',)
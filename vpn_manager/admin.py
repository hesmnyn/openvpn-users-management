import os
import telnetlib
from django.contrib import admin, messages
from django.db import models
from django.contrib.admin.widgets import AdminDateWidget

from django.urls import path
from django.shortcuts import redirect
from django.utils.html import format_html
from django.utils import timezone
from .models import VPNUser
from .utils import get_client_info, get_connected_usernames, get_connected_usernames_from_file
from .utils import kill_user
 

# Management interface configuration
MGMT_HOST = os.getenv('OPENVPN_MGMT_HOST', '127.0.0.1')
MGMT_PORT = int(os.getenv('OPENVPN_MGMT_PORT', 7505))
MGMT_TIMEOUT = int(os.getenv('OPENVPN_MGMT_TIMEOUT', 5))  # seconds

@admin.register(VPNUser)
class VPNUserAdmin(admin.ModelAdmin):
    list_display = (
        'username',
        'openvpn_password',
        'expiry_date',
        'is_active',
        'is_connected',
        'real_address',
        'virtual_address',
        'kill_button',
    )
    list_filter = ('is_active',)
    search_fields = ('username',)
    ordering = ('username',)
    formfield_overrides = {
        models.DateField:    {'widget': AdminDateWidget},
    }
    class Media:
        js = ('vpn_manager/js/admin-copy-cell.js',)
        css = {
            'all': ('vpn_manager/css/admin-copy-cell.css',)
        }

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Fetch current client info once
        self._client_info = get_client_info()
        return qs

    def is_connected(self, obj):
        return obj.username in self._client_info
    is_connected.boolean = True
    is_connected.short_description = 'Connected?'

    def real_address(self, obj):
        return self._client_info.get(obj.username, {}).get('real_address', '')
    real_address.short_description = 'Real Address'

    def virtual_address(self, obj):
        return self._client_info.get(obj.username, {}).get('virtual_address', '')
    virtual_address.short_description = 'Virtual Address'

    def kill_button(self, obj):
        if obj.username in self._client_info:
            url = f"kill/{obj.pk}/"
            return format_html('<a class="button" href="{}">Disconnect</a>', url)
        return '-'
    kill_button.short_description = 'Disconnect'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('kill/<int:pk>/', self.admin_site.admin_view(self.kill_user), name='vpnuser-kill'),
        ]
        return custom_urls + urls

    def kill_user(self, request, pk, *args, **kwargs):
        """Admin view to send kill command via Telnet"""
        obj = self.get_object(request, pk)
        try:
            res = kill_user(obj.username)
            self.message_user(request, f"Sent kill command for {obj.username}", messages.SUCCESS) if res else self.message_user(request, f"Error sending kill command for {obj.username}", messages.ERROR)
        except Exception as e:
            self.message_user(request, f"Error sending kill command for {obj.username}: {e}", messages.ERROR)
        # Redirect back to changelist
        return redirect(request.META.get('HTTP_REFERER', 'admin:index'))
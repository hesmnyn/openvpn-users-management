import os
import telnetlib
from django.contrib import admin, messages
from django.db import models, connection
from django.db.models import F, Value, IntegerField
from django.db.models.functions import Cast, Substr
from django.contrib.admin.widgets import AdminDateWidget
from django.urls import path
from django.shortcuts import redirect
from django.utils.html import format_html

from .models import VPNUser
from .utils import get_client_info, get_connected_usernames, get_connected_usernames_from_file, kill_user

# Management interface configuration
MGMT_HOST = os.getenv('OPENVPN_MGMT_HOST', '127.0.0.1')
MGMT_PORT = int(os.getenv('OPENVPN_MGMT_PORT', 7505))
MGMT_TIMEOUT = int(os.getenv('OPENVPN_MGMT_TIMEOUT', 5))  # seconds

@admin.register(VPNUser)
class VPNUserAdmin(admin.ModelAdmin):
    list_display = (
        'username_natural',
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
    formfield_overrides = {
        models.DateField: {'widget': AdminDateWidget},
    }

    class Media:
        js = ('vpn_manager/js/admin-copy-cell.js',)
        css = {'all': ('vpn_manager/css/admin-copy-cell.css',)}

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Fetch live client info
        self._client_info = get_client_info()

        # Annotate with the numeric part of username for natural sorting
        # Use regex on PostgreSQL, fallback to Substr on SQLite
        vendor = connection.vendor
        if vendor == 'postgresql':
            from django.db.models import Func
            class RegexpReplace(Func):
                function = 'regexp_replace'
                arity = 4

            qs = qs.annotate(
                _username_num=Cast(
                    RegexpReplace(
                        F('username'),
                        Value(r'\D+'),
                        Value(''),
                        Value('g'),
                    ),
                    output_field=IntegerField(),
                )
            )
        else:
            # Assuming usernames have a fixed alphabetic prefix of length 4 (e.g. 'test')
            # Adjust the 5 below if your prefix length differs +1 (start index for digits)
            qs = qs.annotate(
                _username_num=Cast(
                    Substr('username', 5),
                    output_field=IntegerField(),
                )
            )

        # Default ordering by the annotated integer if no user-specified sort
        if 'o' not in request.GET:
            qs = qs.order_by('_username_num')
        return qs

    def username_natural(self, obj):
        return obj.username
    username_natural.admin_order_field = '_username_num'
    username_natural.short_description = 'Username'

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
        obj = self.get_object(request, pk)
        try:
            success = kill_user(obj.username)
            level = messages.SUCCESS if success else messages.ERROR
            msg = f"{'Disconnected' if success else 'Error disconnecting'} {obj.username}"
        except Exception as e:
            level, msg = messages.ERROR, f"Error disconnecting {obj.username}: {e}"
        self.message_user(request, msg, level)
        return redirect(request.META.get('HTTP_REFERER', 'admin:index'))

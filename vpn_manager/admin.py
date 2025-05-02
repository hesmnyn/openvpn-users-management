from django.contrib import admin
from .models import VPNUser
from .utils import get_connected_usernames

@admin.register(VPNUser)
class VPNUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'expiry_date', 'is_active', 'is_connected')
    list_filter  = ('is_active',)
    search_fields = ('username',)
    ordering = ('username',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Pre-fetch connected usernames once per request
        self._connected = get_connected_usernames()
        return qs

    def is_connected(self, obj):
        return obj.username in getattr(self, '_connected', set())
    is_connected.boolean = True
    is_connected.short_description = 'Connected?'
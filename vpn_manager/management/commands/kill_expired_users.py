import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from vpn_manager.models import VPNUser
from django.conf import settings
from datetime import date
from vpn_manager.utils import get_client_info, kill_user
PSW_FILE = settings.OPENVPN_PSW_FILE





class Command(BaseCommand):
    help = 'Kill VPNUser that is expired'

    def handle(self, *args, **options):
        # Filter active, non-expired VPNUsers
        expired_users = VPNUser.objects.filter(has_access_server_user=False).exclude(
            is_active=True, expiry_date__gte=date.today())
        current_users = get_client_info()
        counter = 0
        for user in expired_users:
            if user.username in current_users:
                kill_user(user.username)
                counter+=1
        self.stdout.write(self.style.SUCCESS(f"Killed {counter} users"))

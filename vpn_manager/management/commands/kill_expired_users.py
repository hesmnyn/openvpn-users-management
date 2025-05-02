import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from vpn_manager.models import VPNUser
from django.conf import settings
from datetime import date
from vpn_manager.utils import kill_user
PSW_FILE = settings.OPENVPN_PSW_FILE





class Command(BaseCommand):
    help = 'Kill VPNUser that is expired'

    def handle(self, *args, **options):
        # Filter active, non-expired VPNUsers
        expired_users = VPNUser.objects.exclude(
            is_active=True, expiry_date__gte=date.today())
        for user in expired_users:
            kill_user(user.username)
        self.stdout.write(self.style.SUCCESS(f"Killed {len(expired_users)} users"))

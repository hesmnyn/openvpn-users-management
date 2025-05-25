import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from vpn_manager.models import VPNUser
from django.conf import settings
from datetime import date
PSW_FILE = settings.OPENVPN_PSW_FILE




def _write_users(users):
    """
    Write the users dictionary to the PSW file, one per line in 'username:password:max_connections' format.
    """
    os.makedirs(os.path.dirname(PSW_FILE), exist_ok=True)
    with open(PSW_FILE, 'w') as f:
        for user, data in users.items():
            f.write(f"{user}:{data['password']}:{data['max_connections']}\n")


class Command(BaseCommand):
    help = 'Synchronize VPNUser entries to the OpenVPN PSW file'

    def handle(self, *args, **options):
        # Filter active, non-expired VPNUsers
        active_users = VPNUser.objects.filter(
            is_active=True, expiry_date__gte=date.today(), has_access_server_user=False)
        users = {
            u.username: {
                'password': u.openvpn_password,
                'max_connections': u.max_connections
            }
            for u in active_users
        }

        _write_users(users)
        self.stdout.write(self.style.SUCCESS(
            f"Synced {len(users)} users to {PSW_FILE}"))

        # Mark expired users as inactive
        expired_users = VPNUser.objects.filter(has_access_server_user=False).exclude(
            is_active=True, expiry_date__gte=date.today())
        expired_users.update(is_active=False)

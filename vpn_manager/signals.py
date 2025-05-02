import os
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import VPNUser
from django.conf import settings
from datetime import date
PSW_FILE = settings.OPENVPN_PSW_FILE


def _load_users():
    users = {}
    if os.path.exists(PSW_FILE):
        with open(PSW_FILE) as f:
            for line in f:
                if ':' in line:
                    user, pwd = line.strip().split(':', 1)
                    users[user] = pwd
    return users


def _write_users(users):
    os.makedirs(os.path.dirname(PSW_FILE), exist_ok=True)
    with open(PSW_FILE, 'w') as f:
        for user, pwd in users.items():
            f.write(f"{user}:{pwd}\n")


@receiver(post_save, sender=VPNUser)
def update_psw_file_on_save(sender, instance, **kwargs):
    users = _load_users()
    # If user is active, add/update; otherwise remove
    if instance.is_active and instance.expiry_date >= date.today():
        users[instance.username] = instance.openvpn_password
    else:
        users.pop(instance.username, None)
    _write_users(users)


@receiver(post_delete, sender=VPNUser)
def remove_psw_file_on_delete(sender, instance, **kwargs):
    users = _load_users()
    users.pop(instance.username, None)
    _write_users(users)

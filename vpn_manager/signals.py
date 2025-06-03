import os
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import VPNUser
from .utils import create_user_sacli_commands, kill_user, prop_deny_user_sacli_commands
from django.conf import settings

PSW_FILE = settings.OPENVPN_PSW_FILE


def _load_users():
    users = {}
    if os.path.exists(PSW_FILE):
        with open(PSW_FILE) as f:
            for line in f:
                if ':' in line:
                    user, pwd, max_conns = line.strip().split(':', 2)
                    users[user] = {'password': pwd, 'max_connections': max_conns}
    return users


def _write_users(users):
    os.makedirs(os.path.dirname(PSW_FILE), exist_ok=True)
    with open(PSW_FILE, 'w') as f:
        for user, data in users.items():
            f.write(f"{user}:{data['password']}:{data['max_connections']}\n")


@receiver(pre_save, sender=VPNUser)
def update_psw_file_on_save(sender, instance, **kwargs):
    try:
        old_instance = sender.objects.get(pk=instance.pk)
        if old_instance.has_access_server_user == False and instance.has_access_server_user:
            users = _load_users()
            if users.pop(instance.username, None):
                _write_users(users)
                kill_user(instance.username, instance.has_access_server_user)
            if instance.is_active:
                create_user_sacli_commands(instance.username, instance.openvpn_password)
                prop_deny_user_sacli_commands(instance.username, "false")
        else:
            if instance.has_access_server_user:
                if instance.is_active:
                    create_user_sacli_commands(instance.username, instance.openvpn_password)
                    prop_deny_user_sacli_commands(instance.username, "false")
                elif old_instance.is_active:
                    prop_deny_user_sacli_commands(instance.username, "true")
                    kill_user(instance.username, instance.has_access_server_user)
            else:
                users = _load_users()
                # If user is active, add/update; otherwise remove
                if instance.is_active:
                    users[instance.username] = {
                        'password': instance.openvpn_password,
                        'max_connections': instance.max_connections,
                    }
                elif old_instance.is_active:
                    users.pop(instance.username, None)
                    kill_user(instance.username, instance.has_access_server_user)
                _write_users(users)
        
    except sender.DoesNotExist:
        if instance.is_active:
            if instance.has_access_server_user:
                create_user_sacli_commands(instance.username, instance.openvpn_password)
                prop_deny_user_sacli_commands(instance.username, "false")
                return
            else:
                users = _load_users()
                users[instance.username] = {
                    'password': instance.openvpn_password,
                    'max_connections': instance.max_connections,
                }
                _write_users(users)
                return


@receiver(post_delete, sender=VPNUser)
def remove_psw_file_on_delete(sender, instance, **kwargs):
    users = _load_users()
    users.pop(instance.username, None)
    _write_users(users)
    kill_user(instance.username, instance.has_access_server_user)

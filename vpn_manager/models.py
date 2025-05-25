from django.db import models

class VPNUser(models.Model):
    username = models.CharField(
        max_length=150,
        unique=True,
        help_text="Unique VPN username (can include any characters)",
    )
    openvpn_password = models.CharField(
        max_length=128,
        help_text="Password for OpenVPN connections (separate from Django login)",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the VPN account is active or revoked",
    )
    expiry_date = models.DateField(
        help_text="Date when this user’s VPN credentials expire"
    )
    max_connections = models.PositiveIntegerField(
        default=1,
        help_text="Maximum simultaneous connections for this user",
    )
    has_access_server_user = models.BooleanField(default=True)


    def __str__(self):
        return self.username



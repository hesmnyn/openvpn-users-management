from django.db import models


class VPNUser(models.Model):
    username = models.CharField(
        max_length=150,
        unique=True,
        help_text="Unique VPN username (can include any characters)",
    )
    expiry_date = models.DateField(
        help_text="Date/time when this user’s VPN credentials expire"
    )
    openvpn_password = models.CharField(
        max_length=128,
        help_text="Password for OpenVPN connections (separate from Django login)",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the VPN account is active or revoked",
    )

    def __str__(self):
        return self.username
from django.apps import AppConfig


class VpnManagerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "vpn_manager"
    def ready(self):
        # Ensures signal handlers are registered
        import vpn_manager.signals
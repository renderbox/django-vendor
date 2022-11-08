from django.apps import AppConfig


class VendorConfig(AppConfig):
    name = 'vendor'

    def ready(self):
        import vendor.signals

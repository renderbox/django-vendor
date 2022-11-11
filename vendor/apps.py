from django.apps import AppConfig
class VendorConfig(AppConfig):
    name = 'vendor'

    def ready(self):
        from vendor.config import VENDOR_PAYMENT_PROCESSOR, SupportedPaymentProcessor
        if VENDOR_PAYMENT_PROCESSOR == SupportedPaymentProcessor.STRIPE:
            import vendor.signals.stripe_signals

from django.apps import AppConfig
class VendorConfig(AppConfig):
    name = 'vendor'

    def ready(self):
        from vendor.config import VENDOR_PAYMENT_PROCESSOR, SupportedPaymentProcessor

        if VENDOR_PAYMENT_PROCESSOR == SupportedPaymentProcessor.STRIPE:
            import vendor.signals.stripe_signals
    
    #  TODO: Would be better to find way to check if any sites have stripe configured instead of having to set the VENDOR_PAYMENT_PROCESSOR to stripe 
    # to enable it's signals. You can't do the following way, because you assume that you have already ran migration, but if you are in a fresh install
    # this code will error out any time you run a manage.py command because Site has not been migrated and you are trying to import it. 
    # def ready(self):
    #     from django.contrib.sites.models import Site
    #     from vendor.config import SupportedPaymentProcessor
    #     from vendor.processors import get_site_payment_processor

    #     is_stripe_configured = next((True for site in Site.objects.all() if get_site_payment_processor(site) == SupportedPaymentProcessor.STRIPE), None)

    #     if is_stripe_configured:
    #         import vendor.signals.stripe_signals
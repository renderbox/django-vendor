from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from stripe import Customer
from vendor.models import CustomerProfile, Offer
from vendor.config import PaymentProcessorSiteConfig, SupportedPaymentProcessor
from vendor.processors import StripeProcessor

@receiver(post_save, sender=CustomerProfile)
def stripe_create_customer_signal(sender, instance, created, **kwargs):
    site_configured_processor = PaymentProcessorSiteConfig(instance.site)

    if site_configured_processor.get_key_value('payment_processor') != SupportedPaymentProcessor.STRIPE.value:
        # TODO: logger.error
        return None
    
    if 'stripe_id' in instance.meta:
        return None

    processor = StripeProcessor(instance.site)

    customer_query = {'query': f"email:'{instance.user.email}' AND metadata['site']:'{instance.site}'"}
    query_result = processor.stripe_query(processor.stripe.Customer, customer_query)

    if not query_result.is_empty:
        # TODO: log that user can't be created it needs to be synced
        return None
   
    customer = processor.build_customer(instance)

    instance.meta['stripe_id'] = customer.id
    instance.save()
    # TODO: logger info

@receiver(post_delete, sender=CustomerProfile)
def stripe_delete_customer_signal(sender, instance, **kwargs):
    site_configured_processor = PaymentProcessorSiteConfig(instance.site)

    if site_configured_processor.get_key_value('payment_processor') != SupportedPaymentProcessor.STRIPE.value:
        # TODO: logger.error
        return None
    
    if 'stripe_id' not in instance.meta:
        return None

    processor = StripeProcessor(instance.site)

    processor.stripe_delete(processor.stripe.Customer, instance.meta['stripe_id'])
    # TODO: logger info
    

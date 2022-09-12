import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from stripe import Customer
from vendor.models import CustomerProfile, Offer
from vendor.config import PaymentProcessorSiteConfig, SupportedPaymentProcessor
from vendor.processors import StripeProcessor

logger = logging.getLogger(__name__)

@receiver(post_save, sender=CustomerProfile)
def stripe_create_customer_signal(sender, instance, created, **kwargs):
    site_configured_processor = PaymentProcessorSiteConfig(instance.site)

    if site_configured_processor.get_key_value('payment_processor') != SupportedPaymentProcessor.STRIPE.value:
        logger.error(f"stripe_create_customer_signal instance: {instance.pk} was not created on stripe for site {instance.site} because site is not configured with Stripe")
        return None
    
    if 'stripe_id' in instance.meta:
        return None

    processor = StripeProcessor(instance.site)

    customer_query = {'query': f"email:'{instance.user.email}' AND metadata['site']:'{instance.site}'"}
    query_result = processor.stripe_query_object(processor.stripe.Customer, customer_query)

    if not query_result.is_empty:
        logger.warning(f"stripe_create_customer_signal instance: {instance.pk} is already on stripe, may need to sync it.")
        return None
   
    customer = processor.build_customer(instance)

    instance.meta['stripe_id'] = customer.id
    instance.save()
    logger.success(f"stripe_create_customer_signal instance: {instance.pk} successfully created on Stripe")

@receiver(post_delete, sender=CustomerProfile)
def stripe_delete_customer_signal(sender, instance, **kwargs):
    site_configured_processor = PaymentProcessorSiteConfig(instance.site)

    if site_configured_processor.get_key_value('payment_processor') != SupportedPaymentProcessor.STRIPE.value:
        logger.error(f"stripe_delete_customer_signal instance: {instance.pk} can't be deleted as this site: {instance.site} is not configured to use Stripe")
        return None
    
    if 'stripe_id' not in instance.meta:
        return None

    processor = StripeProcessor(instance.site)

    processor.stripe_delete_object(processor.stripe.Customer, instance.meta['stripe_id'])
    logger.successs(f"stripe_delete_customer_signal instance: {instance.pk} was successfully deleted on Stripe")
    

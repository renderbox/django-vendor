from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from vendor.models import CustomerProfile, Offer

from vendor.integrations import StripeIntegration
from vendor.processors import StripeProcessor

@receiver(post_save, sender=CustomerProfile)
def stripe_create_customer_signal(sender, instance, created, **kwargs):
    stripe_credentials = StripeIntegration(instance.site)

    if not stripe_credentials.instance:
        # TODO: logger.error
        return None
    
    if 'stripe_id' in instance.meta:
        return None

    processor = StripeProcessor(instance.site)

    customers = processor.query_customers()
    customer_query = f"'email': {instance.user.email} AND metadata['site']: {instance.site}"
    search_data = self.stripe_call(stripe.Product.search, {'query': f'name~"{name}"'})

    # TODO: Nice to have stripe data builder
    customer_data = {
        'name': f"{instance.user.first_name} {instance.user.last_name}",
        'email': instance.user.email,
    }
    customer = processor.create_customer(**customer_data)
    instance.meta['stripe_id'] = customer.id
    instance.save()
    # TODO: logger info

@receiver(post_delete, sender=CustomerProfile)
def stripe_delete_customer_signal(sender, instance, **kwargs):
    stripe_credentials = StripeIntegration(instance.site)

    if not stripe_credentials.instance:
        # TODO: logger.error
        return None

    if 'stripe_id' not in instance.meta:
        # TODO: logger.warning
        return None

    processor = StripeProcessor(instance.site)

    processor.delete_customer(instance.meta['stripe_id'])
    # TODO: logger info
    

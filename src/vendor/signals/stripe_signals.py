import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from vendor.config import PaymentProcessorSiteConfig, SupportedPaymentProcessor
from vendor.models import CustomerProfile, Offer
from vendor.processors import StripeProcessor, StripeQueryBuilder

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CustomerProfile, dispatch_uid="stripe_customer_post_save")
def stripe_create_customer_signal(sender, instance, created, **kwargs):
    site_configured_processor = PaymentProcessorSiteConfig(instance.site)

    if site_configured_processor.get_key_value('payment_processor') != SupportedPaymentProcessor.STRIPE.value:
        logger.error(f"stripe_create_customer_signal instance: {instance.pk} was not created on stripe for site {instance.site} because site is not configured with Stripe")
        return None
    
    if 'stripe_id' in instance.meta:
        return None

    processor = StripeProcessor(instance.site)

    query_builder = StripeQueryBuilder()

    email_clause = query_builder.make_clause_template(
        field='email',
        value=instance.user.email,
        operator=query_builder.EXACT_MATCH,
        next_operator=query_builder.AND
    )

    metadata_clause = query_builder.make_clause_template(
        field='metadata',
        key='site',
        value=instance.site.domain,
        operator=query_builder.EXACT_MATCH
    )

    query = query_builder.build_search_query(processor.stripe.Customer, [email_clause, metadata_clause])
    query_result = processor.stripe_query_object(processor.stripe.Customer, query)

    if not processor.transaction_succeeded:
        logger.error(f"stripe_create_customer_signal: {processor.transactions_info}")
        return None 

    post_save.disconnect(sender=CustomerProfile, dispatch_uid="stripe_customer_post_save")
    if query_result:
        logger.info(f"stripe_create_customer_signal: updating customer: {instance}")
        processor.update_stripe_customers([instance])
        if len(query_result.data) > 1:
            logger.warning(f"stripe_create_customer_signal: more than one customer found for email: {instance.user.email} on site: {instance.site.domain}")

    processor.create_stripe_customers([instance])
    post_save.connect(receiver=stripe_create_customer_signal, sender=CustomerProfile, dispatch_uid="stripe_customer_post_save")
    logger.info(f"stripe_create_customer_signal instance: {instance.pk} successfully created on Stripe")


@receiver(post_delete, sender=CustomerProfile, dispatch_uid="stripe_customer_post_delete")
def stripe_delete_customer_signal(sender, instance, **kwargs):
    site_configured_processor = PaymentProcessorSiteConfig(instance.site)

    if site_configured_processor.get_key_value('payment_processor') != SupportedPaymentProcessor.STRIPE.value:
        logger.error(f"stripe_delete_customer_signal instance: {instance.pk} can't be deleted as this site: {instance.site} is not configured to use Stripe")
        return None
    
    if 'stripe_id' not in instance.meta:
        return None

    processor = StripeProcessor(instance.site)

    post_delete.disconnect(sender=CustomerProfile, dispatch_uid="stripe_customer_post_delete")
    processor.stripe_delete_object(processor.stripe.Customer, instance.meta['stripe_id'])
    post_delete.connect(receiver=stripe_delete_customer_signal, sender=CustomerProfile, dispatch_uid="stripe_customer_post_delete")
    logger.info(f"stripe_delete_customer_signal instance: {instance.pk} was successfully deleted on Stripe")


@receiver(post_save, sender=Offer, dispatch_uid="stripe_offer_post_save")
def stripe_create_offer_signal(sender, instance, created, **kwargs):
    site_configured_processor = PaymentProcessorSiteConfig(instance.site)

    if site_configured_processor.get_key_value('payment_processor') != SupportedPaymentProcessor.STRIPE.value:
        logger.error(
            f"stripe_create_offer_signal instance: {instance.pk} was not created on stripe for site {instance.site} because site is not configured with Stripe")
        return None

    processor = StripeProcessor(instance.site)

    query_builder = StripeQueryBuilder()

    pk_clause = query_builder.make_clause_template(
        field='metadata',
        key='pk',
        value=str(instance.pk),
        operator=query_builder.EXACT_MATCH,
        next_operator=query_builder.AND
    )

    metadata_clause = query_builder.make_clause_template(
        field='metadata',
        key='site',
        value=instance.site.domain,
        operator=query_builder.EXACT_MATCH
    )

    query = query_builder.build_search_query(processor.stripe.Product, [pk_clause, metadata_clause])
    query_result = processor.stripe_query_object(processor.stripe.Product, query)

    if not processor.transaction_succeeded:
        logger.error(f"stripe_create_offer_signal: {processor.transactions_info}")
        return None

    post_save.disconnect(sender=Offer, dispatch_uid="stripe_offer_post_save")
    if 'stripe' not in instance.meta:
        instance.meta.update({'stripe': {'product_id': query_result['data'][0]['id']}})
        instance.save()

    if query_result['data']:
        logger.info(f"stripe_create_offer_signal: updating the offer: {instance}")
        processor.update_offers([instance])
    else:
        processor.create_offers([instance])

    post_save.connect(receiver=stripe_create_offer_signal, sender=Offer, dispatch_uid="stripe_offer_post_save")
    logger.info(f"stripe_create_offer_signal instance: offer {instance.pk} successfully created on Stripe")


@receiver(post_delete, sender=Offer, dispatch_uid="stripe_offer_post_delete")
def stripe_delete_offer_signal(sender, instance, **kwargs):
    site_configured_processor = PaymentProcessorSiteConfig(instance.site)

    if site_configured_processor.get_key_value('payment_processor') != SupportedPaymentProcessor.STRIPE.value:
        logger.error(
            f"stripe_delete_offer_signal instance: {instance.pk} can't be deleted as this site: {instance.site} is not configured to use Stripe")
        return None

    if 'stripe' not in instance.meta:
        return None

    processor = StripeProcessor(instance.site)

    post_delete.disconnect(sender=Offer, dispatch_uid="stripe_offer_post_delete")
    processor.stripe_delete_object(processor.stripe.Product, instance.meta['stripe']['product_id'])
    processor.stripe_update_object(processor.stripe.Price, instance.meta['stripe']['price_id'], {'active': False})

    if instance.meta.get('stripe').get('coupon_id'):
        processor.stripe_delete_object(processor.stripe.Coupon, instance.meta['stripe']['coupon_id'])
        logger.info(f"stripe_delete_offer_signal instance: offer {instance.pk} coupon was successfully deleted on Stripe")

    post_delete.connect(receiver=stripe_delete_offer_signal, sender=Offer, dispatch_uid="stripe_offer_post_delete")
    logger.info(f"stripe_delete_offer_signal instance: offer {instance.pk} was successfully deleted on Stripe")

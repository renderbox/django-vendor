import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from stripe import Customer
from vendor.models import CustomerProfile, Offer
from vendor.config import PaymentProcessorSiteConfig, SupportedPaymentProcessor, DEFAULT_CURRENCY
from vendor.processors import StripeProcessor, StripeQueryBuilder


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

    customer_query = {'query': f"email:'{instance.user.email}' AND metadata['site']:'{instance.site.domain}'"}
    query_result = processor.stripe_query_object(processor.stripe.Customer, customer_query)

    if not processor.transaction_succeded:
        logger.error(f"stripe_create_customer_signal: {processor.transactions_info}")
        return None 

    if query_result:
        instance.meta['stripe_id'] = query_result.data[0].id
        instance.save()
        if len(query_result.data) > 1:
            logger.warning(f"stripe_create_customer_signal: more than one customer found for email: {instance.user.email} on site: {instance.site.domain}")
        return None
   
    customer_data = processor.build_customer(instance)
    stripe_customer = processor.stripe_create_object(processor.stripe.Customer, customer_data)

    if not processor.transaction_succeded:
        logger.error(f"stripe_create_customer_signal: {processor.transactions_info}")
        return None 

    instance.meta['stripe_id'] = stripe_customer.id
    instance.save()
    logger.info(f"stripe_create_customer_signal instance: {instance.pk} successfully created on Stripe")


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
    logger.success(f"stripe_delete_customer_signal instance: {instance.pk} was successfully deleted on Stripe")


@receiver(post_save, sender=Offer)
def stripe_create_offer_signal(sender, instance, created, **kwargs):
    site_configured_processor = PaymentProcessorSiteConfig(instance.site)

    if site_configured_processor.get_key_value('payment_processor') != SupportedPaymentProcessor.STRIPE.value:
        logger.error(
            f"stripe_create_offer_signal instance: {instance.pk} was not created on stripe for site {instance.site} because site is not configured with Stripe")
        return None

    if 'stripe' in instance.meta:
        return None

    processor = StripeProcessor(instance.site)

    query_builder = StripeQueryBuilder()

    pk_clause = query_builder.make_clause_template(
        field='metadata',
        key='pk',
        value=instance.pk,
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

    if not processor.transaction_succeded:
        logger.error(f"stripe_create_offer_signal: {processor.transactions_info}")
        return None

    if query_result:
        coupons = processor.get_coupons()
        coupon_matches = processor.match_coupons(coupons, instance)
        product_id = query_result.data[0].id
        price_id = processor.get_price_id_with_product(product_id)
        instance.meta['stripe'] = {
            'product_id': product_id,
            'price_id': price_id
        }

        if coupon_matches:
            instance.meta['coupon_id'] = coupon_matches[0].id

        instance.save()

        if len(coupon_matches) > 1:
            logger.warning(
                f"stripe_create_offer_signal: more than one coupon found for offer: {instance.pk} on site: {instance.site.domain}")

        if len(query_result.data) > 1:
            logger.warning(
                f"stripe_create_offer_signal: more than one offer/product found for pk: {instance.pk} on site: {instance.site.domain}")
        return None

    product_data = processor.build_product(instance)
    stripe_product = processor.stripe_create_object(processor.stripe.Product, product_data)
    instance.meta['stripe'] = {'product_id': stripe_product.id}

    price = instance.get_current_price_instance() if instance.get_current_price_instance() else None
    msrp = instance.get_msrp()
    current_price = msrp
    price_pk = None

    if price:
        current_price = price.cost
        price_pk = price.pk

    price_data = processor.build_price(instance, msrp, current_price, DEFAULT_CURRENCY, price_pk)
    stripe_price = processor.stripe_create_object(processor.stripe.Price, price_data)
    instance.meta['stripe']['price_id'] = stripe_price.id

    if not processor.transaction_succeded:
        logger.error(f"stripe_create_offer_signal: {processor.transactions_info}")
        return None

    if instance.has_any_discount_or_trial():
        coupon_data = processor.build_coupon(instance, DEFAULT_CURRENCY)

        stripe_coupon = processor.stripe_create_object(processor.stripe.Coupon, coupon_data)
        instance.meta['stripe']['coupon_id'] = stripe_coupon.id

    instance.save()
    logger.info(f"stripe_create_offer_signal instance: offer {instance.pk} successfully created on Stripe")


@receiver(post_delete, sender=Offer)
def stripe_delete_offer_signal(sender, instance, **kwargs):
    site_configured_processor = PaymentProcessorSiteConfig(instance.site)

    if site_configured_processor.get_key_value('payment_processor') != SupportedPaymentProcessor.STRIPE.value:
        logger.error(
            f"stripe_delete_offer_signal instance: {instance.pk} can't be deleted as this site: {instance.site} is not configured to use Stripe")
        return None

    if 'stripe' not in instance.meta:
        return None

    processor = StripeProcessor(instance.site)

    processor.stripe_delete_object(processor.stripe.Product, instance.meta['stripe']['product_id'])
    processor.stripe_update_object(processor.stripe.Price, instance.meta['stripe']['price_id'], {'active': False})

    if instance.meta.get('stripe').get('coupon_id'):
        processor.stripe_delete_object(processor.stripe.Coupon, instance.meta['stripe']['coupon_id'])
        logger.success(f"stripe_delete_offer_signal instance: offer {instance.pk} coupon was successfully deleted on Stripe")

    logger.success(f"stripe_delete_offer_signal instance: offer {instance.pk} was successfully deleted on Stripe")

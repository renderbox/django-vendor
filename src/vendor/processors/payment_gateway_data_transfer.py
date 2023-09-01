import logging
from datetime import datetime

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.utils import timezone

from vendor.models import CustomerProfile, Offer, Subscription
from vendor.models.choice import InvoiceStatus, SubscriptionStatus
from vendor.processors import AuthorizeNetProcessor, StripeProcessor

logger = logging.getLogger(__name__)


def convert_authorize_net_submitted_date(submitted_date):
    try:
        submitted_datetime = datetime.strptime(submitted_date.pyval, '%Y-%m-%dT%H:%M:%S.%f%z')
    
    except ValueError as exce:
        logger.error(f"sync_subscriptions_and_create_missing_receipts error {exce}")
        submitted_datetime = datetime.strptime(submitted_date.pyval, '%Y-%m-%dT%H:%M:%S%z')

    return submitted_datetime


def get_last_transaction_datetime(transactions, authorize_net):
    if not transactions:
        return None
    
    if len(transactions) == 1:
        transaction_id = transactions[0].transId.text
        transaction_detail = authorize_net.get_transaction_detail(transaction_id)
        return convert_authorize_net_submitted_date(transaction_detail.submitTimeUTC)
    
    return convert_authorize_net_submitted_date(transactions[0].submitTimeUTC)

def transfer_subscriptions_from_authorizenet_to_stripe(site):
    authorize_net = AuthorizeNetProcessor(site)
    stripe = StripeProcessor(site)

    auth_subscriptions = authorize_net.get_list_of_subscriptions()

    for auth_subscription in auth_subscriptions:
        subscription_info = authorize_net.subscription_info(auth_subscription.id.text)
        logger.info(f"Syncing AuthorizeNet Subscription ID: {auth_subscription.id.text}")
        subscription_transactions = authorize_net.get_subscription_transactions(subscription_info)
        last_transaction_datetime = get_last_transaction_datetime(subscription_transactions, authorize_net)

        if hasattr(subscription_info.subscription.profile, 'email'):
            email = subscription_info.subscription.profile.email.text

            try:
                customer_profile = CustomerProfile.objects.get(site=site, user__email__iexact=email)
                offers = Offer.objects.filter(site=site, name__contains=subscription_info.subscription.name)
                stripe_customer = stripe.get_stripe_customer_from_email(email)
                
                if not stripe_customer:
                    stripe.create_stripe_customers([customer_profile])
                elif stripe_customer and 'stripe_id' not in customer_profile.meta:
                    customer_profile.meta.update({'stripe_id': stripe_customer.id})
                    customer_profile.save()

                stripe_customer = stripe.stripe_get_object(stripe.stripe.Customer, customer_profile.meta['stripe_id'], expand=['subscriptions'])
                
                if 'site' not in stripe_customer['metadata']:
                    stripe.update_stripe_customers([customer_profile])

                if not offers.count():
                    raise ObjectDoesNotExist()
                offer = offers.first()
                
                invoice = customer_profile.get_cart()
                invoice.empty_cart()
                invoice.add_offer(offer)
                stripe.invoice = invoice

                for stripe_customer_subscription in stripe_customer.subscriptions:
                    stripe_product = stripe.stripe_get_object(stripe.stripe.Product, stripe_customer_subscription['plan']['product'])
                    if stripe_product['metadata']['pk'] == str(offer.pk) and 'stripe' not in offer.meta:
                        offer.meta.update({'stripe': {'product_id': stripe_product.id}})
                        offer.save()
                        stripe.sync_offer(offer)
                    if Subscription.objects.filter(profile=customer_profile, gateway_id=stripe_customer_subscription.id).exists():
                        stripe.sync_stripe_subscription(site, stripe_customer_subscription)
                        raise Exception(f"Stripe Subscription Synced {stripe_customer_subscription.id}")
                
                stripe_product = stripe.get_stripe_product(site, offer.pk)
                if not stripe_product:
                    stripe.create_offers([offer])

                if stripe_product and 'stripe' not in offer.meta:
                    offer.meta.update({'stripe': {'product_id': stripe_product.id}})
                    offer.save()
                
                stripe.sync_offer_prices(offer)
                
                stripe_payment_methods = stripe.get_customer_payment_methods(stripe_customer.id)
                if not stripe_payment_methods:
                    raise ObjectDoesNotExist(f"stripe_payment_method does not exist for stripe_customer: {stripe_customer.id}")
                
                setup_intent_object = stripe.build_setup_intent(stripe_payment_methods[0].id)
                stripe_setup_intent = stripe.stripe_create_object(stripe.stripe.SetupIntent, setup_intent_object)
                if not stripe_setup_intent:
                    raise Exception(f"Could not create stripe_setup_intent transaction_info: {stripe.transaction_info}")
                
                subscription_obj = stripe.build_subscription(stripe.invoice.order_items.first(), stripe_payment_methods[0].id)
                trial_days = offer.get_offer_end_date(last_transaction_datetime) - timezone.now()
                subscription_obj['trial_period_days'] = trial_days.days
                subscription_obj['billing_cycle_anchor'] = offer.get_offer_end_date(last_transaction_datetime)
                stripe_subscription = stripe.stripe_create_object(stripe.stripe.Subscription, subscription_obj)

                if not stripe_subscription or stripe_subscription.status == 'incomplete':
                    stripe.transaction_succeeded = False
                    logger.error(f"AuthorizeNet Subscription {auth_subscription.id.text} was not transfered to stripe error {stripe.transaction_info}")
                else:
                    subscription = Subscription.objects.create(
                        gateway_id=stripe_subscription.id,
                        profile=customer_profile,
                        auto_renew=True,
                        status=SubscriptionStatus.ACTIVE
                    )
                    subscription.meta['response'] = stripe.transaction_info
                    subscription.save()

            except ObjectDoesNotExist as exce:
                logger.exception(f"sync_subscriptions exception: {exce} subscription: ({auth_subscription.id.text}, {subscription_info.subscription.name})")
            except MultipleObjectsReturned as exce:
                logger.exception(f"sync_subscriptions exception: {exce} subscription: ({auth_subscription.id.text}, {subscription_info.subscription.name})")
            except Exception as exce:
                logger.exception(f"sync_subscriptions exception: {exce} subscription: ({auth_subscription.id.text}, {subscription_info.subscription.name})")

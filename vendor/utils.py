from calendar import mdays
from datetime import timedelta, datetime, timezone
from decimal import Decimal, ROUND_UP
from django.contrib.sites.shortcuts import get_current_site
from django.utils import timezone

from vendor.models import Subscription, Receipt, Payment, Invoice
from vendor.models.choice import TermDetailUnits, InvoiceStatus
from vendor.processors import AuthorizeNetProcessor


#############
# Requst and Session Utils
def get_site_from_request(request):
    if hasattr(request, 'site'):
        return request.site
    return get_current_site(request)

def get_or_create_session_cart(session):
    session_cart = {}
    if 'session_cart' not in session:
        session['session_cart'] = session_cart
    session_cart = session.get('session_cart')

    return session_cart

def clear_session_purchase_data(request):
    if 'billing_address_form' in request.session:
        del(request.session['billing_address_form'])
    if 'credit_card_form' in request.session:
        del(request.session['credit_card_form'])


def get_future_date_months(today, add_months):
    """
    Returns a datetime object with the a new added months
    """
    newday = today.day
    newmonth = (((today.month - 1) + add_months) % 12) + 1
    newyear = today.year + (((today.month - 1) + add_months) // 12)
    if newday > mdays[newmonth]:
        newday = mdays[newmonth]
    if newyear % 4 == 0 and newmonth == 2:
        newday += 1
    return datetime(newyear, newmonth, newday, tzinfo=timezone.utc)


def get_future_date_days(today, add_days):
    """
    Returns a datetime object with the a new added days
    """
    return today + timedelta(days=add_days)


def get_payment_scheduled_end_date(offer, start_date=timezone.now()):
    """
    Determines the start date offset so the payment gateway starts charging the monthly offer
    """
    units = offer.term_details.get('term_units', TermDetailUnits.MONTH)

    if units == TermDetailUnits.MONTH:
        return get_future_date_months(start_date, offer.get_period_length())
    elif units == TermDetailUnits.DAY:
        return get_future_date_days(start_date, offer.get_period_length())


def get_display_decimal(amount):
    return Decimal(amount).quantize(Decimal('.00'), rounding=ROUND_UP)


def create_subscription_model_form_past_receipts(site):
    processor = AuthorizeNetProcessor(site)

    subscriptions = processor.get_list_of_subscriptions(1000)
    active_subscriptions = [ s for s in subscription_list if s['status'] == 'active' ]

    for sub_detail in active_subscriptions:
        subscription = Subscription()
        past_receipt = Receipt.objects.filter(transaction=sub_detail.id.text).first()
        
        subscription.gateway_id = sub_detail.id.text
        subscription.profile = past_receipt.profile
        subscription.auto_renew = True
        subscription.save()
        
        response = processor.get_subscription_info(sub_detail.id.text)

        for transaction in response.arbTransaction.arbTransaction:
            invoice = Invoice.objects.create(
                status=InvoiceStatus.CHECKOUT,
                site=past_receipt.profile.site,
                profile=past_receipt.profile,
                ordered_date=timezone.now(),
                total=transaction_detail.authAmount.pyval
            )
            invoice.add_offer(past_receipt.order_item.offer)
            invoice.save()

            renew_processor = AuthorizeNetProcessor(site, invoice)
            renew_processor.subscription = subscription
            renew_processor.renew_subscription(transaction_id, {"msg": "Created by create_subscription_model_form_past_receipts"})


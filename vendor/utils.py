from calendar import mdays
from datetime import timedelta, datetime
from decimal import Decimal, ROUND_UP
from django.contrib.sites.shortcuts import get_current_site
from django.utils import timezone

from vendor.models.choice import TermDetailUnits


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

def get_subscription_start_date(offer, profile, start_date=timezone.now()):
    if profile.is_on_trial(offer):
        return start_date + timedelta(days=offer.get_trial_days())
    
    if not profile.has_owned_product(offer.products.all()):
        return start_date + timedelta(days=offer.get_trial_days())

    return start_date
        

def get_display_decimal(amount):
    return Decimal(amount).quantize(Decimal('.00'), rounding=ROUND_UP)



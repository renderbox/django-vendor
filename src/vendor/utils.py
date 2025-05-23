from calendar import mdays
from datetime import datetime, timedelta, timezone
from decimal import ROUND_UP, Decimal

from django.contrib.sites.shortcuts import get_current_site
from django.utils import timezone as dj_timezone
from django.utils.encoding import force_str
from django.utils.functional import Promise


#############
# Requst and Session Utils
def get_site_from_request(request):
    if hasattr(request, "site"):
        return request.site
    return get_current_site(request)


def get_or_create_session_cart(session):
    session_cart = {}
    if "session_cart" not in session:
        session["session_cart"] = session_cart
    session_cart = session.get("session_cart")

    return session_cart


def clear_session_purchase_data(request):
    if "billing_address_form" in request.session:
        del request.session["billing_address_form"]
    if "credit_card_form" in request.session:
        del request.session["credit_card_form"]


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


def get_display_decimal(amount):
    return Decimal(amount).quantize(Decimal(".00"), rounding=ROUND_UP)


def force_str_if_proxy(value):
    """
    Convert Django lazy translation objects (Promise/__proxy__) to string, otherwise return as is.
    """
    if isinstance(value, Promise):
        return force_str(value)
    return value

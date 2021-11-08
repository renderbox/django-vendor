from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View

from vendor.models import Invoice, Offer, Receipt
from vendor.processors import get_site_payment_processor
from vendor.utils import get_or_create_session_cart, get_site_from_request

class VendorIndexAPI(View):
    """
    docstring
    """
    def get(self, request, *args, **kwargs):
        print('index api')
        return HttpResponse('<h1>Welcome to vendor APIs<h1>')


class AddToCartView(View):
    '''
    Create an order item and add it to the order
    '''
    def session_cart(self, request, offer):
        offer_key = str(offer.pk)
        session_cart = get_or_create_session_cart(request.session)

        if offer_key not in session_cart:
            session_cart[offer_key] = {}
            session_cart[offer_key]['quantity'] = 0

        session_cart[offer_key]['quantity'] += 1

        if not offer.allow_multiple:
            session_cart[offer_key]['quantity'] = 1

        return session_cart

    def post(self, request, *args, **kwargs):
        try:
            offer = Offer.objects.get(site=get_site_from_request(request), slug=self.kwargs["slug"], available=True)
        except ObjectDoesNotExist:
            messages.error(_("Offer does not exist or is unavailable"))
            return redirect('vendor:cart')

        if request.user.is_anonymous:
            request.session['session_cart'] = self.session_cart(request, offer)
        else:
            profile, created = self.request.user.customer_profile.get_or_create(site=get_site_from_request(request))

            cart = profile.get_cart_or_checkout_cart()

            if cart.status == Invoice.InvoiceStatus.CHECKOUT:
                cart.status = Invoice.InvoiceStatus.CART
                cart.save()

            if profile.has_product(offer.products.all()) and not offer.allow_multiple:
                messages.info(self.request, _("You Have Already Purchased This Item"))
            elif cart.order_items.filter(offer__products__in=offer.products.all()).count() and not offer.allow_multiple:
                messages.info(self.request, _("You already have this product in you cart. You can only buy one"))
            else:
                messages.info(self.request, _("Added item to cart."))
                cart.add_offer(offer)

        return redirect('vendor:cart')      # Redirect to cart on success


class RemoveFromCartView(View):

    def post(self, request, *args, **kwargs):
        offer = Offer.objects.get(site=get_site_from_request(request), slug=self.kwargs["slug"])
        if request.user.is_anonymous:
            offer_key = str(offer.pk)
            session_cart = get_or_create_session_cart(request.session)

            if offer_key in session_cart:
                session_cart[offer_key]['quantity'] -= 1

            if session_cart[offer_key]['quantity'] <= 0:
                del(session_cart[offer_key])

            request.session['session_cart'] = session_cart
        else:
            profile = self.request.user.customer_profile.get(site=get_site_from_request(request))      # Make sure they have a cart

            cart = profile.get_cart_or_checkout_cart()

            if cart.status == Invoice.InvoiceStatus.CHECKOUT:
                cart.status = Invoice.InvoiceStatus.CART
                cart.save()

            cart.remove_offer(offer)

        messages.info(self.request, _("Removed item from cart."))

        return redirect('vendor:cart')      # Redirect to cart on success


class SubscriptionCancelView(LoginRequiredMixin, View):
    success_url = reverse_lazy('vendor:customer-subscriptions')

    def post(self, request, *args, **kwargs):
        receipt = Receipt.objects.get(uuid=self.kwargs["uuid"])

        processor = get_site_payment_processor(receipt.order_item.invoice.site)(receipt.order_item.invoice)
        processor.subscription_cancel(receipt)

        messages.info(self.request, _("Subscription Cancelled"))

        return redirect(request.META.get('HTTP_REFERER', self.success_url))


class RenewSubscription(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        # TODO: Need to implement
        pass
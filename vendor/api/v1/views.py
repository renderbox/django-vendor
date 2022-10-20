from django.apps import apps
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.views import View

from vendor.config import VENDOR_PRODUCT_MODEL
from vendor.models import CustomerProfile, Invoice, Offer, Receipt, Subscription
from vendor.models.choice import InvoiceStatus
from vendor.processors import get_site_payment_processor
from vendor.utils import get_or_create_session_cart, get_site_from_request


Product = apps.get_model(VENDOR_PRODUCT_MODEL)


class VendorIndexAPI(View):
    """
    docstring
    """
    def get(self, request, *args, **kwargs):
        return HttpResponse('<h1>Welcome to vendor APIs<h1>')


class AddToCartView(View):
    '''
    Create an order item and adds it to the order. No login required as the request can come
    from a user without a session.
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

        if not request.user.is_authenticated:
            request.session['session_cart'] = self.session_cart(request, offer)
        else:
            profile, created = self.request.user.customer_profile.get_or_create(site=get_site_from_request(request))

            cart = profile.get_cart_or_checkout_cart()

            if cart.status == InvoiceStatus.CHECKOUT:
                cart.status = InvoiceStatus.CART
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
    '''
    Removes an order item and adds it to the order. No login required as the request can come
    from a user without a session.
    '''
    def post(self, request, *args, **kwargs):
        offer = get_object_or_404(Offer, site=get_site_from_request(request), slug=self.kwargs["slug"])
        if not request.user.is_authenticated:
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

            if cart.status == InvoiceStatus.CHECKOUT:
                cart.status = InvoiceStatus.CART
                cart.save()

            cart.remove_offer(offer)

        messages.info(self.request, _("Removed item from cart."))
        return redirect('vendor:cart')      # Redirect to cart on success


class SubscriptionCancelView(LoginRequiredMixin, View):
    success_url = reverse_lazy('vendor:customer-subscriptions')

    def post(self, request, *args, **kwargs):
        subscription = get_object_or_404(Subscription, uuid=self.kwargs["uuid"])

        processor = get_site_payment_processor(subscription.profile.site)(subscription.profile.site)
        
        try: 
            processor.subscription_cancel(subscription)

            messages.info(self.request, _("Subscription Cancelled"))

        except Exception as exce:
            messages.warning(self.request, _("You can only cancel subscription if you are on trial or there has been at least one settled payment."))

        return redirect(request.META.get('HTTP_REFERER', self.success_url))


class VoidProductView(LoginRequiredMixin, View):
    success_url = reverse_lazy('vendor_admin:manage-profiles')

    def post(self, request, *args, **kwargs):
        receipt = get_object_or_404(Receipt, uuid=self.kwargs["uuid"])
        receipt.subscription.void()

        messages.info(request, _("Customer has no longer access to Product"))
        return redirect(request.META.get('HTTP_REFERER', self.success_url))


class AddOfferToProfileView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        customer_profile = get_object_or_404(CustomerProfile, uuid=kwargs.get('uuid_profile'))
        offer = get_object_or_404(Offer, uuid=kwargs['uuid_offer'])

        cart = customer_profile.get_cart_or_checkout_cart()
        cart.empty_cart()
        cart.add_offer(offer)

        if offer.current_price() or cart.total:
            messages.info(request, _("Offer and Invoice must have zero value"))
            cart.remove_offer(offer)
            return redirect(reverse('vendor_admin:manager-profile', kwargs={'uuid': customer_profile.uuid}))

        processor = get_site_payment_processor(cart.site)(cart.site, cart)
        processor.authorize_payment()

        messages.info(request, _("Offer Added To Customer Profile"))
        return redirect(reverse('vendor_admin:manager-profile', kwargs={'uuid': customer_profile.uuid}))


class ProductAvailabilityToggleView(LoginRequiredMixin, View):
    success_url = reverse_lazy('vendor_admin:manager-product-list')

    def post(self, request, *args, **kwargs):
        product = get_object_or_404(Product, uuid=self.kwargs.get('uuid'))

        product.available = request.POST.get('available', False)
        product.save()

        for offer in Offer.objects.filter(products__in=[product]):
            offer.available = product.available
            offer.save()

        messages.info(request, _("Product availability Changed"))
        return redirect(request.META.get('HTTP_REFERER', self.success_url))


class SubscriptionPriceUpdateView(LoginRequiredMixin, View):
    success_url = reverse_lazy('vendor_admin:manager-product-list')

    def post(self, request, *args, **kwargs):
        site = get_site_from_request(request)
        subscription = get_object_or_404(Subscription, profile__site=site, uuid=self.request.POST.get('subscription_uuid'))
        offer = get_object_or_404(Offer, site=site, uuid=self.request.POST.get('offer_uuid'))

        processor = get_site_payment_processor(site)(site)
        processor.subscription_update_price(subscription, offer.current_price(), request.user)
        
        return redirect(request.META.get('HTTP_REFERER', self.success_url))


class RenewSubscription(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        # TODO: Need to implement
        pass
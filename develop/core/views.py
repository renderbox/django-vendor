import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import TemplateView, View
from django.views.generic.list import ListView

from vendor.models import Offer
from vendor.forms import CreditCardForm
from vendor.models.choice import PaymentTypes
from vendor.utils import get_site_from_request
from vendor.views.mixin import ProductRequiredMixin


logger = logging.getLogger(__name__)


class VendorIndexView(ListView):
    template_name = "core/index.html"
    model = Offer

    def get_queryset(self):
        if hasattr(self.request, 'site'):
            return self.model.objects.filter(site=get_site_from_request(self.request), available=True)
        return self.model.on_site.filter(available=True)


class ProductAccessView(ProductRequiredMixin, TemplateView):
    model = Offer
    template_name = "core/product_use.html"

    def get(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        context['object'] = self.model.objects.get(site=get_site_from_request(request), slug=kwargs['slug'])
        return render(request, self.template_name, context)

    def get_product_queryset(self):
        """
        Method to get the Product(s) needed for the check.  Can be overridden to handle complex queries.
        """
        return self.model.objects.filter(site=get_site_from_request(self.request), slug=self.kwargs['slug']).get().products.all()

class AccountView(LoginRequiredMixin, TemplateView):
    template_name = "core/account.html"

    def get(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        
        customer_profile, created = request.user.customer_profile.get_or_create(site=get_site_from_request(request))
        subscriptions = customer_profile.get_recurring_receipts()

        context['payments'] = customer_profile.payments.filter(success=True)
        context["offers"] = Offer.objects.filter(site=get_site_from_request(request), available=True).order_by('terms')

        if subscriptions:
            context['subscription'] = subscriptions.first()
            context['payment'] = subscriptions.first().order_item.invoice.payments.filter(success=True).first()
            context['payment_form'] = CreditCardForm(initial={'payment_type': PaymentTypes.CREDIT_CARD})

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        return render(request, self.template_name, context)

class LoggerTestView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        logger.debug("Debug Test Logger")
        logger.info("info Test Logger")
        logger.warning("warning Test Logger")
        logger.error("error Test Logger")
        logger.critical("critical Test Logger")

        return JsonResponse({"msgs": "testing logger"})

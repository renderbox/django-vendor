from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.models import Site
from django.shortcuts import render
from django.utils import timezone
from django.views.generic import TemplateView
from django.views.generic.list import ListView

from vendor.models import Offer, Payment
from vendor.views.mixin import ProductRequiredMixin
from vendor.forms import CreditCardForm
from vendor.models.choice import PurchaseStatus, TermType, PaymentTypes

class VendorIndexView(ListView):
    template_name = "core/index.html"
    model = Offer
    queryset = Offer.objects.filter(available=True)


class ProductAccessView(ProductRequiredMixin, TemplateView):
    model = Offer
    template_name = "core/product_use.html"

    def get(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.model.on_site.get(slug=kwargs['slug'])
        return render(request, self.template_name, context)

    def get_product_queryset(self):
        """
        Method to get the Product(s) needed for the check.  Can be overridden to handle complex queries.
        """
        return self.model.on_site.filter(slug=self.kwargs['slug']).get().products.all()

class AccountView(LoginRequiredMixin, TemplateView):
    template_name = "core/account.html"

    def get(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        customer_profile, created = request.user.customer_profile.get_or_create(site=Site.objects.get_current())
        subscription = customer_profile.receipts.filter(status__gte=PurchaseStatus.COMPLETE, 
                                                        order_item__offer__terms__gt=TermType.PERPETUAL, 
                                                        order_item__offer__terms__lt=TermType.ONE_TIME_USE,
                                                        start_date__lte=timezone.now(),
                                                        end_date__gte=timezone.now()).first()
        
        context['payments'] = customer_profile.payments.filter(success=True)
        context["offers"] = Offer.on_site.filter(available=True).order_by('terms')

        if subscription:
            context['subscription'] = subscription
            context['payment'] = subscription.order_item.invoice.payments.get(success=True).first()
            context['payment_form'] = CreditCardForm(initial={'payment_type': PaymentTypes.CREDIT_CARD})
            
        
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)


        return render(request, self.template_name, context)
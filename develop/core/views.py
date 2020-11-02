from django.shortcuts import render
from django.views.generic import TemplateView
from django.views.generic.list import ListView

# from vendor.mixins import UserOwnsProductMixin
from vendor.models import Offer
from vendor.views.mixin import ProductRequiredMixin


class VendorIndexView(ListView):
    template_name = "core/index.html"
    model = Offer

class ProductAccessView(TemplateView):
    model = Offer
    template_name = "core/product_use.html"


    def get(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        if context['owens_product']:
            context['object'] = Offer.objects.get(slug=kwargs['slug'])

        return render(request, self.template_name, context)

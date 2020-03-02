from django.views.generic import TemplateView
from django.views.generic.list import ListView

from core.models import Product
from vendor.models import ProductOffer

class VendorIndexView(ListView):
    template_name = "core/index.html"
    model = ProductOffer

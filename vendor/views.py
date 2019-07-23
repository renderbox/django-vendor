from django.views.generic import TemplateView

class VendorIndexView(TemplateView):
    template_name = "vendor/index.html"

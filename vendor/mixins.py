# TODO: Need to think of a better way to check if a user has product in a mixin
# from django.apps import apps
# from django.conf import settings
# from .config import VENDOR_PRODUCT_MODEL
# Product = apps.get_model(VENDOR_PRODUCT_MODEL)

# class UserOwnsProductMixin(object):
#     """Verify if user has product to view"""
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         product = Product.objects.get(slug=self.kwargs["slug"])
        
#         context['owns_product'] = self.request.user.customer_profile.get(site=settings.SITE_ID).has_product(product)
        
#         return context
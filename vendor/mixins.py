from django.conf import settings
from vendor.models import Offer

class UserOwnsProductMixin(object):
    """Verify if user has product to view"""
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        offer = Offer.objects.get(slug=self.kwargs["slug"])
        
        context['owens_product'] = self.request.user.customer_profile.get(site=settings.SITE_ID).has_offer(offer)
        
        return context
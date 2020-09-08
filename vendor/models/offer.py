import uuid

from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.core.exceptions import FieldError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext as _

from autoslug import AutoSlugField

from .base import CreateUpdateModelBase

from .choice import TermType

#########
# OFFER
#########

class Offer(CreateUpdateModelBase):
    '''
    Offer attaches to a record from the designated VENDOR_PRODUCT_MODEL.  
    This is so more than one offer can be made per product, with different 
    priorities.
    '''
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)                                # Used to track the product
    slug = AutoSlugField(populate_from='name', unique_with='site__id')                                               # SEO friendly 
    site = models.ForeignKey(Site, on_delete=models.CASCADE, default=settings.SITE_ID, related_name="product_offers")                      # For multi-site support
    name = models.CharField(_("Name"), max_length=80, blank=True)                                           # If there is only a Product and this is blank, the product's name will be used, oterhwise it will default to "Bundle: <product>, <product>""
    product = models.ForeignKey(settings.VENDOR_PRODUCT_MODEL, on_delete=models.CASCADE, related_name="offers", blank=True, null=True)         # TODO: Combine with bundle field?
    bundle = models.ManyToManyField(settings.VENDOR_PRODUCT_MODEL, related_name="bundles", blank=False)  # Used in the case of a bundles/packages.  Bundles override individual products
    start_date = models.DateTimeField(_("Start Date"), help_text="What date should this offer become available?")
    end_date = models.DateTimeField(_("End Date"), blank=True, null=True, help_text="Expiration Date?")
    terms =  models.IntegerField(_("Terms"), default=0, choices=TermType.choices)
    term_details = models.JSONField(_("Term Details"), default=dict, blank=True, null=True)
    term_start_date = models.DateTimeField(_("Term Start Date"), help_text="When is this product available to use?", blank=True, null=True) # Useful for Event Tickets or Pre-Orders
    available = models.BooleanField(_("Available"), default=False, help_text="Is this currently available?")

    objects = models.Manager()
    on_site = CurrentSiteManager()

    class Meta:
        verbose_name = _("Offer")
        verbose_name_plural = _("Offers")

    def __str__(self):
        return self.name

    def current_price(self):
        '''
        Check if there are any price options active, otherwise use msrp.
        '''
        now = timezone.now()
        price_before_tax, price_after_tax = 0, 0
        
        if self.prices.all().count() == 0:                                                         # Check if offer has prices
            price_before_tax = float(self.product.meta.split(',')[1])# TODO: Implement MSRP from product/bundles                        # No prices default to product MSRP
        else:
            if self.prices.filter(start_date__lte=now):                         # Check if offer start date is less than or equal to now
                if self.prices.filter(start_date__lte=now, end_date__gte=now):  # Check if is between two start and end date. return depending on priority
                    price_before_tax = self.prices.filter(start_date__lte=now, end_date__gte=now).order_by('priority').last().cost
                else:                                                           # Return acording to start date and priority
                    price_before_tax = self.prices.filter(start_date__lte=now).order_by('priority').last().cost
            else:                
                # TODO: need to validate if it is a bundle                        # Only future start date. Default to MSRP
                if self.product.meta:
                    price_before_tax = float(self.product.meta.split(',')[1]) # TODO: Implement MSRP from product with country code 
                else:                    
                    raise FieldError(_("There is no price set on Offer or MSRP on Product"))
        
        # price_after_tax = price_before_tax * self.product.tax_classifier.tax_rule.tax   TODO: implement tax_classifier and tax rule and bundle
        price_after_tax = price_before_tax
        
        return price_after_tax

    def add_to_cart_link(self):
        return reverse("vendor:add-to-cart", kwargs={"slug":self.slug})

    def remove_from_cart_link(self):
        return reverse("vendor:remove-from-cart", kwargs={"slug":self.slug})

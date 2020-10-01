import uuid

from autoslug import AutoSlugField
from decimal import Decimal, ROUND_UP
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.core.exceptions import FieldError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext as _
from iso4217 import Currency

from vendor.config import VENDOR_PRODUCT_MODEL, DEFAULT_CURRENCY

from .base import CreateUpdateModelBase
from .choice import TermType
from .utils import set_default_site_id
#########
# OFFER
#########

class Offer(CreateUpdateModelBase):
    '''
    Offer attaches to a record from the designated VENDOR_PRODUCT_MODEL.  
    This is so more than one offer can be made per product, with different 
    priorities.  It also allows for the bundling of several products into
    a single Offer on the site.
    '''
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)                                # Used to track the product
    slug = AutoSlugField(populate_from='name', unique_with='site__id')                                               # SEO friendly 
    site = models.ForeignKey(Site, on_delete=models.CASCADE, default=set_default_site_id, related_name="product_offers")                      # For multi-site support
    name = models.CharField(_("Name"), max_length=80, blank=True)                                           # If there is only a Product and this is blank, the product's name will be used, oterhwise it will default to "Bundle: <product>, <product>""
    start_date = models.DateTimeField(_("Start Date"), help_text="What date should this offer become available?")
    end_date = models.DateTimeField(_("End Date"), blank=True, null=True, help_text="Expiration Date?")
    terms =  models.IntegerField(_("Terms"), default=0, choices=TermType.choices)
    term_details = models.JSONField(_("Term Details"), default=dict, blank=True, null=True)
    term_start_date = models.DateTimeField(_("Term Start Date"), help_text=_("When is this product available to use?"), blank=True, null=True) # Useful for Event Tickets or Pre-Orders
    available = models.BooleanField(_("Available"), default=False, help_text=_("Is this currently available?"))
    bundle = models.BooleanField(_("Is a Bundle?"), default=False, help_text=_("Is this a product bundle? (auto-generated)"))  # Auto-generated based on if the count of the products is greater than 1.
    offer_description = models.TextField(_("Offer Description"), blank=True, null=True)

    objects = models.Manager()
    on_site = CurrentSiteManager()

    class Meta:
        verbose_name = _("Offer")
        verbose_name_plural = _("Offers")

    def __str__(self):
        return self.name

    def get_msrp(self, currency=DEFAULT_CURRENCY):
        return sum([p.get_msrp(currency) for p in self.products.all()])

    def current_price(self, currency=DEFAULT_CURRENCY):
        '''
        Finds the highest priority active price and returns that, otherwise returns msrp total.
        '''
        now = timezone.now()
        price = self.prices.filter( Q(start_date__lte=now) | Q(start_date=None),
                                    Q(end_date__gte=now) | Q(end_date=None)
                                    ).order_by('-priority').first()            # first()/last() returns the model object or None

        if price:
            result = price.cost
        else:
            result = self.get_msrp(currency)                            # If there is no price for the offer, all MSRPs should be summed up for the "price". 

        return result

    def add_to_cart_link(self):
        return reverse("vendor:add-to-cart", kwargs={"slug":self.slug})

    def remove_from_cart_link(self):
        return reverse("vendor:remove-from-cart", kwargs={"slug":self.slug})
    
    def set_name_if_empty(self):
        product_names = [ product.name for product in self.products.all() ]
        if len(product_names) == 1:
            self.name = product_names[0]
        else:
            self.name = "Bundle: " + ", ".join(product_names)

    @property
    def description(self):
        if self.offer_description:
            return self.offer_description
        else:
            return self.products.all().first().description
    
    def savings(self, currency=DEFAULT_CURRENCY):
        savings = self.get_msrp(currency) - self.current_price()
        if savings < 0:
            return Decimal(0).quantize(Decimal('.00'), rounding=ROUND_UP)
        return Decimal(savings).quantize(Decimal('.00'), rounding=ROUND_UP)

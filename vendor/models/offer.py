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
from django.utils.translation import ugettext_lazy as _
from iso4217 import Currency

from vendor.config import VENDOR_PRODUCT_MODEL, DEFAULT_CURRENCY

from .base import CreateUpdateModelBase
from .choice import TermType, TermDetailUnits
from .utils import set_default_site_id, is_currency_available
#########
# OFFER
#########
def offer_term_details_default():
    return { "term_units": TermDetailUnits.MONTH, "trial_occurrences": 1}

class ActiveManager(models.Manager):
    """
    This Model Manger returns offers that are available
    """
    def get_queryset(self):
        return super().get_queryset().filter(available=True)

class ActiveCurrentSiteManager(CurrentSiteManager):
    """
    This Model Manager return offers per site that are available
    """
    def get_queryset(self):
        return super().get_queryset().filter(available=True)


class Offer(CreateUpdateModelBase):
    '''
    Offer attaches to a record from the designated VENDOR_PRODUCT_MODEL.  
    This is so more than one offer can be made per product, with different 
    priorities.  It also allows for the bundling of several products into
    a single Offer on the site.
    '''
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)                                # Used to track the product
    slug = AutoSlugField(populate_from='name', unique_with='site__id')                                               # SEO friendly 
    site = models.ForeignKey(Site, verbose_name=_("Site"), on_delete=models.CASCADE, default=set_default_site_id, related_name="product_offers")                      # For multi-site support
    name = models.CharField(_("Name"), max_length=80, blank=True)                                           # If there is only a Product and this is blank, the product's name will be used, oterhwise it will default to "Bundle: <product>, <product>""
    start_date = models.DateTimeField(_("Start Date"), help_text=_("What date should this offer become available?"))
    end_date = models.DateTimeField(_("End Date"), blank=True, null=True, help_text=_("Expiration Date?"))
    terms =  models.IntegerField(_("Terms"), default=0, choices=TermType.choices)
    term_details = models.JSONField(_("Term Details"), default=offer_term_details_default, blank=True, null=True, help_text=_("term_units: 10/20(Day/Month), trial_occurrences: 1(defualt)"))
    term_start_date = models.DateTimeField(_("Term Start Date"), help_text=_("When is this product available to use?"), blank=True, null=True) # Useful for Event Tickets or Pre-Orders
    available = models.BooleanField(_("Available"), default=False, help_text=_("Is this currently available?"))
    bundle = models.BooleanField(_("Is a Bundle?"), default=False, help_text=_("Is this a product bundle? (auto-generated)"))  # Auto-generated based on if the count of the products is greater than 1.
    offer_description = models.TextField(_("Offer Description"), default=None, blank=True, null=True, help_text=_("You can enter a list of descriptions. Note: if you inputs something here the product description will not show up."))
    list_bundle_items = models.BooleanField(_("List Bundled Items"), default=False, help_text=_("When showing to customers, display the included items in a list?"))
    allow_multiple = models.BooleanField(_("Allow Multiple Purchase"), default=False, help_text=_("Confirm the user wants to buy multiples of the product where typically there is just one purchased at a time."))

    objects = models.Manager()
    on_site = CurrentSiteManager()
    active = ActiveManager()
    on_site_active = ActiveCurrentSiteManager()

    class Meta:
        verbose_name = "Offer"
        verbose_name_plural = "Offers"

    def __str__(self):
        return self.name

    def get_msrp(self, currency=DEFAULT_CURRENCY):
        """
        Gets the sum of the products msrp cost for products.
        It assumes that all product in a offer use the same currency
        """
        currency = self.get_best_currency(currency)
        return sum([product.get_msrp(currency) for product in self.products.all()])

    def current_price(self, currency=DEFAULT_CURRENCY):
        '''
        Finds the highest priority active price and returns that, otherwise returns msrp total.
        '''
        now = timezone.now()
        price = self.prices.filter( Q(start_date__lte=now) | Q(start_date=None),
                                    Q(end_date__gte=now) | Q(end_date=None),
                                    Q(currency=currency)).order_by('-priority').first()            # first()/last() returns the model object or None

        if price is None:
            return self.get_msrp(currency)                            # If there is no price for the offer, all MSRPs should be summed up for the "price". 
        elif price.cost is None:
            return self.get_msrp(currency)                            # If there is no price for the offer, all MSRPs should be summed up for the "price". 

        return price.cost

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
        """
        Gets the savings between the difference between the product's msrp and the currenct price
        """
        savings = self.get_msrp(currency) - self.current_price(currency)
        if savings < 0:
            return Decimal(0).quantize(Decimal('.00'), rounding=ROUND_UP)
        return Decimal(savings).quantize(Decimal('.00'), rounding=ROUND_UP)

    def get_best_currency(self, currency=DEFAULT_CURRENCY):
        """
        Gets best currency for prodcuts available in this offer
        """
        product_msrp_currencies = [ set(product.meta['msrp'].keys()) for product in self.products.all() ]

        if is_currency_available(product_msrp_currencies[0].union(*product_msrp_currencies[1:]), currency=currency):
            return currency

        return DEFAULT_CURRENCY


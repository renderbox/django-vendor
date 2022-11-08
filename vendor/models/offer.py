import uuid
import math
from autoslug import AutoSlugField
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from vendor.config import DEFAULT_CURRENCY
from vendor.utils import get_payment_scheduled_end_date

from .base import CreateUpdateModelBase, SoftDeleteModelBase
from .choice import TermType, TermDetailUnits
from .utils import set_default_site_id, is_currency_available
from .modelmanagers import ActiveManager, ActiveCurrentSiteManager, CurrentSiteSoftDeleteManager


#########
# OFFER
#########
def offer_term_details_default():
    """
    Sets the default term values as a monthly subscription for a
    period of 12 months, with 0 trial months
    """
    return {
        "period_length": 1,
        "payment_occurrences": 12,
        "term_units": TermDetailUnits.MONTH,
        "trial_occurrences": 0,
        "trial_amount": 0,
        "trial_days": 0
    }


class Offer(SoftDeleteModelBase, CreateUpdateModelBase):
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
    terms = models.IntegerField(_("Terms"), default=0, choices=TermType.choices)
    term_details = models.JSONField(_("Term Details"), default=offer_term_details_default, blank=True, null=True, help_text=_("term_units: 10/20(Day/Month), trial_occurrences: 1(defualt)"))
    term_start_date = models.DateTimeField(_("Term Start Date"), help_text=_("When is this product available to use?"), blank=True, null=True)  # Useful for Event Tickets or Pre-Orders
    available = models.BooleanField(_("Available"), default=False, help_text=_("Is this currently available?"))
    bundle = models.BooleanField(_("Is a Bundle?"), default=False, help_text=_("Is this a product bundle? (auto-generated)"))  # Auto-generated based on if the count of the products is greater than 1.
    offer_description = models.TextField(_("Offer Description"), default=None, blank=True, null=True, help_text=_("You can enter a list of descriptions. Note: if you inputs something here the product description will not show up."))
    list_bundle_items = models.BooleanField(_("List Bundled Items"), default=False, help_text=_("When showing to customers, display the included items in a list?"))
    allow_multiple = models.BooleanField(_("Allow Multiple Purchase"), default=False, help_text=_("Confirm the user wants to buy multiples of the product where typically there is just one purchased at a time."))
    meta = models.JSONField(_("Meta"), default=dict, blank=True, null=True)

    objects = models.Manager()
    on_site = CurrentSiteManager()
    active = ActiveManager()
    on_site_active = ActiveCurrentSiteManager()
    on_site_not_deleted = CurrentSiteSoftDeleteManager()

    class Meta:
        verbose_name = "Offer"
        verbose_name_plural = "Offers"

    def __str__(self):
        return self.name

    def get_status_display(self):
        if self.end_date is not None and timezone.now() > self.end_date:
            return _("Expired")
        elif timezone.now() < self.start_date:
            return _("Scheduled")
        elif timezone.now() >= self.start_date:
            return _("Active")

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
        price = self.prices.filter(Q(start_date__lte=now) | Q(start_date=None),
                                   Q(end_date__gte=now) | Q(end_date=None),
                                   Q(currency=currency)).order_by('-priority').first()  # first()/last() returns the model object or None

        if price is None:
            # If there is no price for the offer, all MSRPs should be summed up for the "price".
            return self.get_msrp(currency)

        elif price.cost is None:
            # If there is no price for the offer, all MSRPs should be summed up for the "price".
            return self.get_msrp(currency)

        return price.cost

    def get_current_price_instance(self, currency=DEFAULT_CURRENCY):
        now = timezone.now()
        price = self.prices.filter(Q(start_date__lte=now) | Q(start_date=None),
                                   Q(end_date__gte=now) | Q(end_date=None),
                                   Q(currency=currency)).order_by('-priority').first()  # first()/last() returns the model object or None

        return price

    def add_to_cart_link(self):
        return reverse("vendor_api:add-to-cart", kwargs={"slug": self.slug})

    def remove_from_cart_link(self):
        return reverse("vendor_api:remove-from-cart", kwargs={"slug": self.slug})

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
        elif self.products.count():
            return self.products.all().first().description.get("description", "")
        else:
            return ""

    def discount(self, currency=DEFAULT_CURRENCY):
        """
        Gets the savings between the difference between the product's msrp and the current price
        """
        discount = self.get_msrp(currency) - self.current_price(currency)

        if discount <= 0:
            return 0
            
        return discount

    def get_best_currency(self, currency=DEFAULT_CURRENCY):
        """
        Gets best currency for products available in this offer
        """
        product_msrp_currencies = [ set(product.meta['msrp'].keys()) for product in self.products.all() ]

        if product_msrp_currencies and len(product_msrp_currencies[0]) >= 2:  # fixes IndexError: list index out of range
            if is_currency_available(product_msrp_currencies[0].union(*product_msrp_currencies[1:]), currency=currency):
                return currency

        return DEFAULT_CURRENCY

    def get_trial_amount(self):
        return self.term_details.get('trial_amount', 0)

    def get_trial_savings(self):
        """
        Returns the savings compared to the current_price of the offer.
        """
        if not self.has_trial_occurrences():
            return 0

        trial_savings = self.current_price() - self.term_details.get('trial_amount', 0)

        if trial_savings < 0:
            return 0

        return trial_savings

    def get_trial_discount(self):
        """
        Returns the trial_amount if the offer has any trial occurrences.
        """
        if not self.has_trial_occurrences():
            return 0

        return self.term_details.get('trial_amount', 0)

    def get_trial_duration_in_months(self):
        duration = self.term_details.get('trial_days', 0)

        if duration <= 0:
            return 0

        return math.ceil(duration/31)

    def has_trial_occurrences(self):
        if self.term_details.get('trial_occurrences', 0) > 0:
            return True
        return False

    def get_next_billing_date(self):
        start_date = timezone.now()
        if self.term_start_date:
            start_date = self.term_start_date
        return get_payment_scheduled_end_date(self, start_date)

    def get_period_length(self):
        if self.terms == TermType.SUBSCRIPTION:
            return self.term_details['period_length']
        else:
            return self.terms - 100   # You subtract 100 because enum are numbered according to their period length. eg Month = 101 and Year = 112

    def get_payment_occurrences(self):
        """
        Gets the defined payment ocurrences for a Subscription. It defaults to
        9999 which means it will charge that amount until the customer cancels the subscription.
        """
        return self.term_details.get('payment_occurrences', 9999)

    def get_trial_occurrences(self):
        return self.term_details.get('trial_occurrences', 0)

    def get_trial_amount(self):
        return self.term_details.get('trial_amount', 0)
    
    def get_trial_days(self):
        return self.term_details.get('trial_days', 0)

    def has_any_discount_or_trial(self):
        if self.discount() or self.get_trial_amount() or\
           self.get_trial_occurrences() or self.get_trial_days():
            return True
            
        return False
    
    def get_term_start_date(self, start_date=timezone.now()):
        if self.term_start_date and self.term_start_date > start_date:
            return self.term_start_date
        
        return start_date


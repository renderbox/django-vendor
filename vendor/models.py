import uuid
import random
import string
import pycountry

from django.utils import timezone
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext as _
from django.urls import reverse
from django.contrib.sites.models import Site
from django.db.models.signals import post_save
from django.utils.text import slugify

from jsonfield import JSONField

##########
# CHOICES
##########

# https://en.wikipedia.org/wiki/ISO_4217
# CURRENCY_CHOICES = [(int(cur.numeric), cur.name) for cur in pycountry.currencies]
CURRENCY_CHOICES = [('usd', 'US Dollar')]

INVOICE_STATUS_CHOICES = (
                (0, _("Cart")), 
                (10, _("Queued")), 
                (20, _("Processing")), 
                (30, _("Failed")), 
                (40, _("Complete")) 
            )

TERM_CHOICES = ((0, _("Perpetual")), (10, _("Subscription")), (20, _("One-Time Use")) )

PURCHASE_STATUS_CHOICES = (
                (0, _("Queued")), 
                (10, _("Processing")), 
                (20, _("Expired")), 
                (30, _("Hold")), 
                (40, _("Canceled")), 
                (50, _("Refunded")), 
                (60, _("Completed")) 
            )

REGION_TYPE_CHOICES = (
                (0, _("Country")), 
                (10, _("State/Province")), 
                (20, _("County")), 
                (30, _("City")), 
            )


############
# UTILITIES
############

def random_string(length=8, check=[]):
    letters= string.digits + string.ascii_uppercase
    value = ''.join(random.sample(letters,length))

    if value not in check:
        return value
    return random_string(length=length, check=check)

def generate_sku():
    return random_string()


##################
# BASE MODELS
##################

class CreateUpdateModelBase(models.Model):
    created = models.DateTimeField("date created", auto_now_add=True)
    updated = models.DateTimeField("last updated", auto_now=True)

    class Meta:
        abstract = True


class ProductBase(CreateUpdateModelBase):
    '''
    This is the base class that all Products should inherit from.
    '''
    sku = models.CharField(_("SKU"), max_length=40, blank=True, null=True, help_text="User Defineable SKU field")                 # Needs to be autogenerated by default, and unique from the PK
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)                                # Used to track the product
    name = models.CharField(_("Name"), max_length=80, blank=True)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, default=settings.SITE_ID, related_name="products")                      # For multi-site support
    slug = models.SlugField(_("Slug"), blank=True, null=True)   # Gets set in the save
    available = models.BooleanField(_("Available"), default=False, help_text="Is this currently available?")                        # This can be forced to be unavailable if there is no prices attached.
    description = models.TextField(blank=True, null=True)
    msrp = JSONField(_("MSRP"), default=dict, blank=True, null=True)     # MSRP in various currencies
    classification = models.ManyToManyField("vendor.ProductClassifier", blank=True)        # What taxes can apply to this item

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)  # Have to make this unique
        super().save(*args, **kwargs)


#########
# MIXINS
#########


#########
# TAXES
#########

# class TaxInfo(models.Model):
#     '''
#     This is meant to start with a simple sales tax estimation.
#     It will likely tie to someting from a 3rd party service, like Avalara eventually.
#     It will still indicate the type of product it is for tax purposes.
#     By default, they should only be set-up in the location where the business is run from.
#     '''
#     name = models.CharField(_("Name"), max_length=80, blank=True)
#     rate = models.FloatField()
#     currency = models.IntegerField(_("Currency"), choices=CURRENCY_CHOICES)  # ISO 4217 Standard codes
#     start_date = models.DateTimeField(_("Start Date"), help_text="When should this tax rate start?")
#     description = models.TextField(_("Description"))
#     region_type = models.IntegerField(choices=REGION_TYPE_CHOICES)  # Where does this tax apply
#     region_name = models.CharField()


#####################
# Product Classifier
#####################

class ProductClassifier(models.Model):
    '''
    This for things like "Digital Goods", "Furniture" or "Food" which may or
    may not be taxable depending on the location.  These are determined by the
    manager of all sites.
    '''
    name = models.CharField(_("Name"), max_length=80, blank=True)
    taxable = models.BooleanField()
    # info = models.ManyToManyField("vendor.TaxInfo")                 # Which taxes is this subject to and where.  This is for a more complex tax setup

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Product Classifier")
        verbose_name_plural = _("Product Classifiers")


#########
# OFFER
#########

class Offer(CreateUpdateModelBase):
    '''
    Offer attaches to a record from the designated PRODUCT_MODEL.  
    This is so more than one offer can be made per product, with different 
    priorities.
    '''
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)                                # Used to track the product
    slug = models.SlugField(_("Slug"), blank=True, null=True)                                               # Gets set in the save, has to be unique
    site = models.ForeignKey(Site, on_delete=models.CASCADE, default=settings.SITE_ID, related_name="product_offers")                      # For multi-site support
    name = models.CharField(_("Name"), max_length=80, blank=True)                                           # If there is only a Product and this is blank, the product's name will be used, oterhwise it will default to "Bundle: <product>, <product>""
    product = models.ForeignKey(settings.PRODUCT_MODEL, on_delete=models.CASCADE, related_name="offers", blank=True, null=True)         # TODO: Combine with bundle field?
    bundle = models.ManyToManyField(settings.PRODUCT_MODEL, related_name="bundles", blank=True)  # Used in the case of a bundles/packages.  Bundles override individual products
    start_date = models.DateTimeField(_("Start Date"), help_text="What date should this offer become available?")
    end_date = models.DateTimeField(_("End Date"), blank=True, null=True, help_text="Expiration Date?")
    terms =  models.IntegerField(_("Terms"), default=0, choices=TERM_CHOICES)
    term_details = JSONField(_("Details"), default=dict, blank=True, null=True)
    term_start_date = models.DateTimeField(_("Term Start Date"), help_text="When is this product available to use?", blank=True, null=True) # Useful for Event Tickets or Pre-Orders
    available = models.BooleanField(_("Available"), default=False, help_text="Is this currently available?")

    class Meta:
        verbose_name = _("Offer")
        verbose_name_plural = _("Offers")

    def __str__(self):
        return self.name

    def current_price(self):
        '''
        Check if there are any price options active, otherwise use msrp.
        '''
        return self.prices.order_by('priority').first().cost

        # TODO: Need to be updated with a query that takes into account date ranges

        # try:
        #     price = self.sale_price.filter( start_date__lte=timezone.now(), end_date__gte=timezone.now() ).order_by('priority').first().cost
        # except:
        #     try:
        #         price = self.sale_price.filter( start_date__lte=timezone.now()).order_by('priority').first().cost
        #     except:
        #         pass

        # return price


    # def current_price(self):
    #     return 20.00

    def add_to_cart_link(self):
        return reverse("vendor:add-to-cart", kwargs={"slug":self.slug})

    def remove_from_cart_link(self):
        return reverse("vendor:remove-from-cart", kwargs={"slug":self.slug})

    def save(self, *args, **kwargs):
        if not self.name:      
            self.name = self.product.name

        self.slug = slugify(self.name)       # TODO: unique slug
        super().save(*args, **kwargs)
    

class Price(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="prices")
    cost = models.FloatField()
    currency = models.CharField(_("Currency"), max_length=4, choices=CURRENCY_CHOICES, default=settings.DEFAULT_CURRENCY)      # USer's default currency
    start_date = models.DateTimeField(_("Start Date"), help_text="When should the price first become available?")
    end_date = models.DateTimeField(_("End Date"), blank=True, null=True, help_text="When should the price expire?")
    priority = models.IntegerField(_("Priority"), help_text="Higher number takes priority", blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.priority:       # TODO: Add check to see if this is the only price on the offer, then let it be 0.  If not, might need to do some assumptions to guess what it should be.
            self.priority = 0

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Price")
        verbose_name_plural = _("Prices")

    def __str__(self):
        return "{} for {}:{}".format(self.offer.name, self.currency, self.cost)


class CustomerProfile(CreateUpdateModelBase):
    '''
    Additional customer information related to purchasing.
    This is what the Invoices are attached to.  This is abstracted from the user model directly do it can be mre flexible in the future.
    '''
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("User"), null=True, on_delete=models.SET_NULL, related_name="customer_profile")
    currency = models.CharField(_("Currency"), max_length=4, choices=CURRENCY_CHOICES, default=settings.DEFAULT_CURRENCY)      # USer's default currency
    site = models.ForeignKey(Site, on_delete=models.CASCADE, default=settings.SITE_ID, related_name="customer_profile")                      # For multi-site support

    class Meta:
        verbose_name = _("Customer Profile")
        verbose_name_plural = _("Customer Profiles")

    def __str__(self):
        return "{} Customer Profile".format(self.user.username)

    def get_cart(self):
        cart, created = self.invoices.get_or_create(status=0)
        return cart


class Address(models.Model):
    name = models.CharField(_("Name"), max_length=80, blank=True)                                           # If there is only a Product and this is blank, the product's name will be used, oterhwise it will default to "Bundle: <product>, <product>""
    profile = models.ForeignKey(CustomerProfile, verbose_name=_("Customer Profile"), null=True, on_delete=models.CASCADE, related_name="addresses")


class Invoice(CreateUpdateModelBase):
    '''
    An invoice starts off as a Cart until it is puchased, then it becomes an Invoice.
    '''
    profile = models.ForeignKey(CustomerProfile, verbose_name=_("Customer Profile"), null=True, on_delete=models.CASCADE, related_name="invoices")
    site = models.ForeignKey(Site, on_delete=models.CASCADE, default=settings.SITE_ID, related_name="invoices")                      # For multi-site support
    status = models.IntegerField(_("Status"), choices=INVOICE_STATUS_CHOICES, default=0)
    customer_notes = models.TextField(blank=True, null=True)
    vendor_notes = models.TextField(blank=True, null=True)
    ordered_date = models.DateTimeField(_("Ordered Date"), blank=True, null=True)               # When was the purchase made?
    subtotal = models.FloatField(default=0.0)                                   
    tax = models.FloatField(blank=True, null=True)                              # Set on checkout
    shipping = models.FloatField(blank=True, null=True)                         # Set on checkout
    total = models.FloatField(blank=True, null=True)                            # Set on purchase
    currency = models.CharField(_("Currency"), max_length=4, choices=CURRENCY_CHOICES, default=settings.DEFAULT_CURRENCY)      # USer's default currency # ISO 4217 Standard 3 char codes
    shipping_address = models.ForeignKey(Address, verbose_name=_("Shipping Address"), on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")

    def __str__(self):
        return "%s Invoice (%s)" % (self.profile.user.username, self.created.strftime('%Y-%m-%d %H:%M'))

    def add_offer(self, offer):
        order_item, created = self.order_items.get_or_create(offer=offer)

        if not created:
            order_item.quantity += 1
            order_item.save()

        self.update_totals()
        self.save()
        return order_item

    def remove_offer(self, offer):
        try:
            order_item = self.order_items.get(offer=offer)      # Get the order item if it's present
        except:
            return 0

        order_item.quantity -= 1

        if order_item.quantity == 0:
            order_item.delete()
        else:
            order_item.save()

        self.update_totals()
        self.save()
        return order_item

    def calculate_shipping(self):
        '''
        Based on the Shipping Address
        '''
        self.shipping = 6.95

    def calculate_tax(self):
        '''
        Based on the Shipping Address
        '''
        self.tax = round(self.subtotal * 0.1, 2)

    def update_totals(self):
        self.subtotal = sum([item.total for item in self.order_items.all() ])

        self.calculate_shipping()
        self.calculate_tax()
        self.total = self.subtotal + self.tax + self.shipping


    # def save(self):
    #     pass
    # DEFAULT_CURRENCY



class OrderItem(CreateUpdateModelBase):
    '''
    A link for each item to a user after it's been purchased
    '''
    invoice = models.ForeignKey(Invoice, verbose_name=_("Invoice"), on_delete=models.CASCADE, related_name="order_items")
    offer = models.ForeignKey(Offer, verbose_name=_("Offer"), on_delete=models.CASCADE, related_name="order_items")
    quantity = models.IntegerField(_("Quantity"), default=1)

    class Meta:
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")

    def __str__(self):
        return "%s - %s" % (self.invoice.profile.user.username, self.offer.name)

    @property
    def total(self):
        return self.quantity * self.price

    @property
    def price(self):
        return self.offer.current_price()

    @property
    def name(self):
        return self.offer.product.name


class Payment(models.Model):
    '''
    Payments
    - Payments are typically from a Credit Card, PayPal or ACH
    - Multiple Payments can be applied to an invoice
    - Gift cards can be used as payments
    - Discounts are Payment credits
    '''
    invoice = models.ForeignKey(Invoice, verbose_name=_("Invoice"), on_delete=models.CASCADE, related_name="payments")
    created = models.DateTimeField("date created", auto_now_add=True)
    transaction = models.CharField(_("Transaction ID"), max_length=50)
    provider = models.CharField(_("Payment Provider"), max_length=16)
    amount = models.FloatField(_("Amount"))
    profile = models.ForeignKey(CustomerProfile, verbose_name=_("Purchase Profile"), blank=True, null=True, on_delete=models.SET_NULL, related_name="payments")
    billing_address = models.ForeignKey(Address, verbose_name=_("payments"), on_delete=models.CASCADE, blank=True, null=True)
    result = models.TextField(_("Result"), blank=True, null=True)
    success = models.BooleanField(_("Successful"), default=False)


class Reciept(CreateUpdateModelBase):
    '''
    A link for all the purchases a user has made. Contains subscription start and end date.
    This is generated for each item a user purchases so it can be checked in other code.
    '''

    profile = models.ForeignKey(CustomerProfile, verbose_name=_("Purchase Profile"), null=True, on_delete=models.CASCADE, related_name="reciepts")
    order_item = models.ForeignKey('vendor.OrderItem', verbose_name=_("Order Item"), on_delete=models.CASCADE, related_name="reciepts")
    product = models.ForeignKey(settings.PRODUCT_MODEL, on_delete=models.CASCADE, related_name="reciepts", blank=True, null=True)           # Goal is to make it easier to check to see if a user owns the product.
    start_date = models.DateTimeField(_("Start Date"), blank=True, null=True)
    end_date = models.DateTimeField(_("End Date"), blank=True, null=True)
    auto_renew = models.BooleanField(_("Auto Renew"), default=False)        # For subscriptions
    vendor_notes = models.TextField()
    transaction = models.CharField(_("Transaction"), max_length=80)
    status = models.IntegerField(_("Status"), choices=PURCHASE_STATUS_CHOICES, default=0)       # Fulfilled, Refund
    class Meta:
        verbose_name = _("Reciept")
        verbose_name_plural = _("Reciepts")

    def __str__(self):
        return "%s - %s - %s" % (self.profile.user.username, self.order_item.offer.name, self.created.strftime('%Y-%m-%d %H:%M'))


class Wishlist(models.Model):
    profile = models.ForeignKey(CustomerProfile, verbose_name=_("Purchase Profile"), null=True, on_delete=models.CASCADE, related_name="wishlists")
    name = models.CharField(_("Name"), max_length=100, blank=False)

    class Meta:
        verbose_name = _("Wishlist")
        verbose_name_plural = _("Wishlists")

    def __str__(self):
        return self.name


class WishlistItem(CreateUpdateModelBase):
    '''
    
    '''
    wishlist = models.ForeignKey(Wishlist, verbose_name=_("Wishlist"), on_delete=models.CASCADE, related_name="wishlist_items")
    offer = models.ForeignKey(Offer, verbose_name=_("Offer"), on_delete=models.CASCADE, related_name="wishlist_items")

    class Meta:
        verbose_name = _("Wishlist Item")
        verbose_name_plural = _("Wishlist Items")
        # TODO: Unique Name Per User

    def __str__(self):
        return "({}) {}: {}".format(self.wishlist.profile.user.username, self.wishlist.name, self.offer.name)


# class Discount(models.Model):
#     pass


# class GiftCode(models.Model):
#     pass


############
# SIGNALS
############

# post_save.connect(create_price_object, sender=Offer, dispatch_uid="create_price_object")

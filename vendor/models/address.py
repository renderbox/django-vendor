import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .profile import CustomerProfile

#####################
# ADDRESS
#####################

class Country(models.IntegerChoices):
    """
    Following ISO 3166
    https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes
    """
    
    # AUS = 36, _("Australia")
    # CAN = 124, _("Canada")
    # JPN = 392, _("Japan")
    # MEX = 484, _("Mexico")
    USA = 581, _("United States")

# Can be overridden in the settings.py with a differnt IntegerChoices object
# It should still maintain the ISO-3166 codes for the country numbers and Enumerated keys
COUNTRY_CHOICE = getattr(settings, 'VENDOR_COUNTRY_CHOICE', Country.choices)
COUNTRY_DEFAULT = getattr(settings, 'VENDOR_COUNTRY_DEFAULT', Country.USA)

class Address(models.Model):
    """Address model for use in purchasing.

    Example:
        Format Fields.

        Gartenweg 8         [address1]
                            [address2]
        Rafing              [locality]
        AUSTRIA             [country]
        3741 PULKAU         [postal code]

    Args:
        name (int): What to name the address if they want to identify it for future use.  Default is "Home"
        profile (CustomerProfile): Foreign Key connection to the Customer Profile
        address_1 (str):

    Returns:
        Address(): Returns an instance of the Address model
    """
    uuid = models.UUIDField(_("UUID"), editable=False, unique=True, default=uuid.uuid4, null=False, blank=False)
    name = models.CharField(_("Address Name"), max_length=80, blank=True)                                           # If there is only a Product and this is blank, the product's name will be used, oterhwise it will default to "Bundle: <product>, <product>""
    profile = models.ForeignKey(CustomerProfile, verbose_name=_("Customer Profile"), null=True, on_delete=models.CASCADE, related_name="addresses")
    first_name = models.CharField(_("First Name"), max_length=150, blank=True)
    last_name = models.CharField(_("Last Name"), max_length=150, blank=True)
    address_1 = models.CharField(_("Address"), max_length=40, blank=False)
    address_2 = models.CharField(_("Address 2 (Optional)"), max_length=40, blank=True, null=True)
    locality = models.CharField(_("City"), max_length=40, blank=False)
    state = models.CharField(_("State"), max_length=40, blank=False)
    country = models.IntegerField(_("Country/Region"), choices=COUNTRY_CHOICE, default=COUNTRY_DEFAULT)
    postal_code = models.CharField(_("Postal Code"), max_length=16, blank=True)

    # def create_address_from_billing_form(self, billing_form, profile):
    #     locality = Locality()
    #     locality.postal_code = billing_form.data.get('postal_code')
    #     locality.name = billing_form.data.get('postal_code')
    #     locality.state = State.objects.get(pk=billing_form.data.get('state'))
    #     locality.save()

    #     address = Address()
    #     # TODO: regex to only get digits
    #     address.street_number = billing_form.data.get('address_line_1')
    #     address.route = ", ".join([billing_form.data.get('address_line_1', ""),billing_form.data.get('address_line_2', "")])
    #     address.locality = locality
    #     address.raw = ", ".join(
    #         [   billing_form.data.get('name', ""),
    #             billing_form.data.get('address_line_1', ""),
    #             billing_form.data.get('address_line_2', ""), 
    #             billing_form.data.get('city', ""), 
    #             State.objects.get(pk=billing_form.data.get('state', "")).name, 
    #             Country.objects.get(pk=billing_form.data.get('country', "")).name,
    #             billing_form.data.get('postal_code', "")
    #             ])
    #     address.save()
        
    #     self.name = 'Billing: {}'.format(profile.user.username)
    #     self.profile = profile
    #     self.address = address.raw

    def __str__(self):
        return "\n".join([ f"{key}: {value}" for key, value in self.__dict__.items() ])
        
    def get_address_display(self):
        return f"{self.profile.user}\n{self.address_1}, {self.address_2}\n{self.locality}, {self.state}, {self.postal_code}".replace('None', '')
         

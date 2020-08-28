
from django.db import models
from django.utils.translation import ugettext as _

from address.models import AddressField, Country, State, Locality, Address
from .profile import CustomerProfile

#####################
# ADDRESS
#####################

class Address(models.Model):
    """Address model for use in purchasing.

    Example:
        Potential Format to use.

        Frau                [title]
        Mag. Maria Muster   [recipient]
        Gartenweg 8         [address1]
                            [address2]
        Rafing              [locality]
        3741 PULKAU         [postal code]
        AUSTRIA             [country]

    Args:
        name (int): The name of the address to use
        profile (CustomerProfile): Foreign Key connection to the Customer Profile
        address (Address): Special Address fields

    Returns:
        Address(): Returns an instance of the Address model
    """
    name = models.CharField(_("Name"), max_length=80, blank=True)                                           # If there is only a Product and this is blank, the product's name will be used, oterhwise it will default to "Bundle: <product>, <product>""
    profile = models.ForeignKey(CustomerProfile, verbose_name=_("Customer Profile"), null=True, on_delete=models.CASCADE, related_name="addresses")
    address = AddressField()


    def create_address_from_billing_form(self, billing_form, profile):
        locality = Locality()
        locality.postal_code = billing_form.data.get('postal_code')
        locality.name = billing_form.data.get('postal_code')
        locality.state = State.objects.get(pk=billing_form.data.get('state'))
        locality.save()

        address = Address()
        # TODO: regex to only get digits
        address.street_number = billing_form.data.get('address_line_1')
        address.route = ", ".join([billing_form.data.get('address_line_1', ""),billing_form.data.get('address_line_2', "")])
        address.locality = locality
        address.raw = ", ".join(
            [   billing_form.data.get('name', ""),
                billing_form.data.get('address_line_1', ""),
                billing_form.data.get('address_line_2', ""), 
                billing_form.data.get('city', ""), 
                State.objects.get(pk=billing_form.data.get('state', "")).name, 
                Country.objects.get(pk=billing_form.data.get('country', "")).name,
                billing_form.data.get('postal_code', "")
                ])
        address.save()
        
        self.name = 'Billing: {}'.format(profile.user.username)
        self.profile = profile
        self.address = address.raw


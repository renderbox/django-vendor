from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings

from vendor.models import Offer, Price, Invoice, OrderItem, Receipt, CustomerProfile, Payment
from vendor.forms import BillingAddressForm, CreditCardForm

User = get_user_model()

class VendorAPITest(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=2)
        self.client.force_login(self.user)

    def test_webhook_authcapture(self):
        url = reverse('vendor_api:api-authorizenet-authcapture-get')
        payload = {
                "responseCode":1,
                "authCode":"77JLY8",
                "avsResponse":"Y",
                "authAmount":112.98,
                "invoiceNumber":"1",
                "entityName":"transaction",
                "id":"60160039986"}
        headers = {'X-Anet-Signature': 'sha512=C83D2EC65F4ADD4771B35FD0BD1EFF135F33ACDF6CA3E9467C05A465D32F985001F1BC46C6E4CADE62FC4C6B77B0A93124D77079B4EDF5B988C311555E6E5A90'}
        response = self.client.post(url, data=payload, **headers)
        pass
    
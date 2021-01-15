import json
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings
from unittest import skipIf

from vendor.models import Offer, Price, Invoice, OrderItem, Receipt, CustomerProfile, Payment
from vendor.forms import BillingAddressForm, CreditCardForm

User = get_user_model()


class VendorAPITest(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        pass
@skipIf(True, "Webhook tests are highly dependent on data in Authroizenet and local data.")
class AuthorizeNetAPITest(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=2)
        self.client.force_login(self.user)

    def test_webhook_authcapture(self):
        url = reverse('vendor_api:api-authorizenet-authcapture-get')
        payload = {
            "notificationId": "afc50fb2-a243-44ec-8e6c-fda7d35ecbec",
            "eventType": "net.authorize.payment.authcapture.created",
            "eventDate": "2021-01-12T08:48:41.6171054Z",
            "webhookId": "2e2b1218-11b5-4fc8-bf6b-652e33cb25ac",
            "payload": json.dumps({
                "responseCode": 1,
                "authCode": "77JLY8",
                "avsResponse": "Y",
                "authAmount": 112.98,
                "invoiceNumber": "1",
                "entityName": "transaction",
                "id": "60160039986"})
            }
        headers = {
            'HTTP_X_ANET_SIGNATURE': 'sha512=C83D2EC65F4ADD4771B35FD0BD1EFF135F33ACDF6CA3E9467C05A465D32F985001F1BC46C6E4CADE62FC4C6B77B0A93124D77079B4EDF5B988C311555E6E5A90',
            'Content-Type': 'application/json'}
        response = self.client.post(url, data=payload, **headers)
    
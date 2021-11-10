import json
import re
from django.contrib.auth import get_user_model
from django.http.response import Http404
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from unittest import skipIf

from vendor.processors.base import PaymentProcessorBase
from vendor.models import Offer, Price, Invoice, OrderItem, Receipt, CustomerProfile, Payment

User = get_user_model()


class VendorAPITest(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)

    def test_subscription_price_update_success(self):
        receipt = Receipt.objects.get(pk=3)
        offer = Offer.objects.get(pk=4)
        price = Price.objects.create(offer=offer, cost=89.99, currency='usd', start_date=timezone.now())
        offer.prices.add(price)

        url = reverse('vendor_api:manager-subscription-price-update')

        response = self.client.post(url, data={"receipt_uuid": receipt.uuid, "offer_uuid": offer.uuid})

        receipt.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertIn('price_update', receipt.vendor_notes.keys())



    def test_subscription_price_update_fail(self):
        url = reverse('vendor_api:manager-subscription-price-update')
        response = self.client.post(url, data={"receipt_uuid": "188e45aa-0fdf-4877-ba84-f4c39c0fc41b", "offer_uuid": "188e45aa-0fdf-4877-ba84-f4c39c0fc41b"})

        self.assertEqual(response.status_code, 404)

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
    
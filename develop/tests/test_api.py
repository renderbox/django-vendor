import json
from datetime import timedelta
from decimal import Decimal
from unittest import skipIf

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from vendor.forms import DateTimeRangeForm
from vendor.models import Offer, Payment, Price, Subscription

User = get_user_model()


class VendorAPITest(TestCase):

    fixtures = ["user", "unit_test"]

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)

    def test_subscription_price_update_success(self):
        subscription = Subscription.objects.get(pk=1)
        offer = Offer.objects.get(pk=4)
        price = Price.objects.create(
            offer=offer,
            cost=89.99,
            currency="usd",  # TODO: should use the ISO4217 for this instead of hardcoding "usd"
            start_date=timezone.now(),
        )
        offer.prices.add(price)

        url = reverse("vendor_api:manager-subscription-price-update")

        response = self.client.post(
            url, data={"subscription_uuid": subscription.uuid, "offer_uuid": offer.uuid}
        )

        subscription.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertIn("price_update", subscription.meta)

    def test_subscription_price_update_fail(self):
        url = reverse("vendor_api:manager-subscription-price-update")
        response = self.client.post(
            url,
            data={
                "subscription_uuid": "188e45aa-0fdf-4877-ba84-f4c39c0fc41b",
                "offer_uuid": "188e45aa-0fdf-4877-ba84-f4c39c0fc41b",
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_refund_payment_success(self):
        payment = Payment.objects.get(pk=1)
        url = reverse("vendor_api:refund-payment-api", kwargs={"uuid": payment.uuid})

        form_data = {
            "refund_amount": 400,
            "reason": "duplicate",
        }

        response = self.client.post(url, form_data)

        self.assertEqual(json.loads(response.content)["message"], "Payment Refunded")

    def test_refund_payment_fail(self):
        payment = Payment.objects.get(pk=1)
        url = reverse("vendor_api:refund-payment-api", kwargs={"uuid": payment.uuid})

        form_data = {
            "refund_amount": 9000,
            "reason": "duplicate",
        }

        response = self.client.post(url, form_data)
        self.assertIn("refund_amount", json.loads(response.content)["error"])

    def test_partial_refund_payment_success(self):
        payment = Payment.objects.get(pk=1)
        url = reverse("vendor_api:refund-payment-api", kwargs={"uuid": payment.uuid})

        form_data = {
            "refund_amount": 200,
            "reason": "duplicate",
        }

        response = self.client.post(url, form_data)
        self.assertEqual(json.loads(response.content)["message"], "Payment Refunded")

        response = self.client.post(url, form_data)
        self.assertEqual(json.loads(response.content)["message"], "Payment Refunded")

        payment.refresh_from_db()

        self.assertEqual(
            sum(Decimal(refund["amount"]) for refund in payment.result["refunds"]),
            form_data["refund_amount"] * 2,
        )

    def test_partial_refund_payment_fail(self):
        payment = Payment.objects.get(pk=1)
        url = reverse("vendor_api:refund-payment-api", kwargs={"uuid": payment.uuid})

        form_data = {
            "refund_amount": 200,
            "reason": "duplicate",
        }

        response = self.client.post(url, form_data)
        self.assertEqual(json.loads(response.content)["message"], "Payment Refunded")

        form_data["refund_amount"] = 900
        response = self.client.post(url, form_data)
        self.assertIn("refund_amount", json.loads(response.content)["error"])

    def test_get_payment_refund_form(self):
        payment = Payment.objects.get(pk=1)
        url = reverse("vendor_api:refund-payment-api", kwargs={"uuid": payment.uuid})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)


@skipIf(
    True, "Webhook tests are highly dependent on data in Authroizenet and local data."
)
class AuthorizeNetAPITest(TestCase):

    fixtures = ["user", "unit_test"]

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=2)
        self.client.force_login(self.user)

    def test_webhook_authcapture(self):
        url = reverse("vendor_api:api-authorizenet-authcapture")
        payload = {
            "notificationId": "afc50fb2-a243-44ec-8e6c-fda7d35ecbec",
            "eventType": "net.authorize.payment.authcapture.created",
            "eventDate": "2021-01-12T08:48:41.6171054Z",
            "webhookId": "2e2b1218-11b5-4fc8-bf6b-652e33cb25ac",
            "payload": json.dumps(
                {
                    "responseCode": 1,
                    "authCode": "77JLY8",
                    "avsResponse": "Y",
                    "authAmount": 112.98,
                    "invoiceNumber": "1",
                    "entityName": "transaction",
                    "id": "60193948919",
                }
            ),
        }
        headers = {
            "HTTP_X_ANET_SIGNATURE": "sha512=C83D2EC65F4ADD4771B35FD0BD1EFF135F33ACDF6CA3E9467C05A465D32F985001F1BC46C6E4CADE62FC4C6B77B0A93124D77079B4EDF5B988C311555E6E5A90",  # noqa E501
            "Content-Type": "application/json",
        }
        response = self.client.post(url, data=payload, **headers)
        self.assertEqual(
            response.status_code, 200
        )  # confims that the webhook was received

    def test_get_settled_transactions_view(self):
        start_date, end_date = (
            timezone.datetime.now() - timedelta(days=3)
        ), timezone.datetime.now()
        form = DateTimeRangeForm(
            initial={"start_date": start_date, "end_date": end_date}
        )

        url = reverse("vendor_api:api-authorizenet-settled-transactions")

        response = self.client.post(url, form.initial)

        self.assertTrue(response)

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from vendor.models import Invoice, Receipt, Payment, receipt

User = get_user_model()


class PaymentModelTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        pass

    def test_get_related_receipts_success(self):
        correct_receipt = Receipt.objects.get(pk=2)
        payment = Payment.objects.get(pk=1)
        receipts = payment.get_related_receipts()
        self.assertTrue(receipts.count())
        self.assertEquals(correct_receipt.pk, receipts.first().pk)

    def test_get_related_receipts_fail(self):
        payment = Payment.objects.get(pk=1)
        payment.transaction = "123"
        payment.save()
        receipts = payment.get_related_receipts()
        self.assertFalse(receipts.count())

    def test_get_receipt(self):
        receipt = Receipt.objects.get(pk=3)
        payment = Payment.objects.get(pk=2)

        self.assertEqual(receipt.pk, payment.get_receipt().pk)


class PaymentViewTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)

    def test_view_payment_status_code(self):
        response = self.client.get(reverse("vendor:purchase-summary", kwargs={'uuid': Invoice.objects.get(pk=1).uuid}))

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Purchase Confirmation')

    def test_view_payment_status_code_fail_no_login(self):
        client = Client()
        response = client.get(reverse("vendor:purchase-summary", kwargs={'uuid': Invoice.objects.get(pk=1).uuid}))

        self.assertEquals(response.status_code, 302)
        self.assertIn('login', response.url)

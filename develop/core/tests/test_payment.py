from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from vendor.models import Invoice, Receipt, Payment

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
        payment = Payment.objects.get(pk=1)
        receipt = Receipt.objects.get(pk=2)

        self.assertEqual(receipt.pk, payment.get_receipt().pk)

    def test_soft_delete(self):
        payment = Payment.objects.all().first()
        payment_count_before_deletion = Payment.objects.all().count()
        payment.delete()

        deleted_payment_difference = Payment.objects.all().count() - Payment.not_deleted.count()

        self.assertEqual(Payment.objects.all().count() - deleted_payment_difference, Payment.not_deleted.count())
        self.assertEquals(payment_count_before_deletion, Payment.objects.all().count())

    def test_get_settled_payments_in_date_range_success(self):
        raise NotImplemented

    def test_get_settled_payments_in_date_range_fail(self):
        raise NotImplemented

    def get_reports_manager(self):
        raise NotImplemented


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

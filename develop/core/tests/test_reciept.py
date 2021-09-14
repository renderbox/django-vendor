from django.contrib.sites.models import Site
from django.test import TestCase
from django.utils import timezone

from vendor.models import Receipt, Offer, Invoice, CustomerProfile
from vendor.utils import get_payment_schedule_end_date


class ReceiptModelTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.first_receipt = Receipt.objects.get(pk=3)
        self.new_invoice = Invoice.objects.create(
            profile=CustomerProfile.objects.get(pk=1),
            site=Site.objects.get(pk=1),
        )
        self.new_invoice.add_offer(Offer.objects.get(pk=4))
        self.new_receipt = Receipt.objects.create(
            start_date=timezone.now(),
            end_date=get_payment_schedule_end_date(self.new_invoice.order_items.first().offer),
            profile=CustomerProfile.objects.get(pk=1),
            order_item=self.new_invoice.order_items.first(),
            transaction=self.first_receipt.transaction
        )

    def test_receipt_is_on_trial_true(self):
        self.first_receipt.start_date = timezone.now()
        self.first_receipt.end_date = get_payment_schedule_end_date(self.first_receipt.order_item.offer)
        self.first_receipt.save()
        self.assertTrue(self.new_receipt.is_on_trial())

    def test_receipt_is_on_trial_false(self):
        self.assertFalse(self.new_receipt.is_on_trial())

    def test_soft_delete(self):
        receipt = Receipt.objects.all().first()
        receipt_count_before_deletion = Receipt.objects.all().count()
        receipt.delete()

        deleted_receipt_difference = Receipt.objects.all().count() - Receipt.not_deleted.count()

        self.assertEqual(Receipt.objects.all().count() - deleted_receipt_difference, Receipt.not_deleted.count())
        self.assertEquals(receipt_count_before_deletion, Receipt.objects.all().count())


class ReceiptViewTests(TestCase):

    fixtures = []

    def setUp(self):
        pass

    def test_view_receipt_status_code(self):
        # TODO: Implement Test
        pass
    
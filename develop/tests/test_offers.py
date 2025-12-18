from datetime import timedelta

from core.models import Product
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from vendor.models import Offer
from vendor.models.choice import TermDetailUnits
from vendor.utils import (
    get_display_decimal,
    get_future_date_days,
    get_future_date_months,
)

User = get_user_model()


class ModelOfferTests(TestCase):

    fixtures = ["user", "unit_test"]

    def setUp(self):
        pass

    def test_create_offer(self):
        offer = Offer()
        offer.name = "test-offer"
        offer.start_date = timezone.now()
        offer.save()
        offer.products.add(Product.objects.all().first())
        pass

    def test_default_site_id(self):
        offer = Offer()
        offer.name = "test-offer"
        offer.start_date = timezone.now()
        offer.save()
        offer.products.add(Product.objects.all().first())

        self.assertEqual(Site.objects.get_current(), offer.site)

    def test_add_offer_to_cart_slug(self):
        mug_offer = Offer.objects.get(pk=4)
        slug = mug_offer.add_to_cart_link()
        self.assertEqual(slug, "/api/cart/add/" + mug_offer.slug + "/")

    def test_remove_offer_to_cart_slug(self):
        mug_offer = Offer.objects.get(pk=4)
        slug = mug_offer.remove_from_cart_link()
        self.assertEqual(slug, "/api/cart/remove/" + mug_offer.slug + "/")

    def test_get_current_price_is_msrp(self):
        offer = Offer.objects.get(pk=4)
        price = offer.current_price("mxn")
        self.assertEqual(price, 21.12)

    def test_get_current_price_is_msrp_default(self):
        offer = Offer.objects.get(pk=4)
        price = offer.current_price()
        self.assertEqual(price, 25.2)

    def test_get_current_price_has_only_start_date(self):
        offer = Offer.objects.get(pk=2)
        self.assertEqual(offer.current_price(), 75.0)

    def test_get_current_price_is_between_start_end_date(self):
        offer = Offer.objects.get(pk=3)
        self.assertEqual(offer.current_price(), 25.2)

    def test_get_current_price_acording_to_priority(self):
        offer = Offer.objects.get(pk=3)
        self.assertEqual(offer.current_price(), 25.2)

    def test_offer_negative_discount(self):
        offer = Offer.objects.get(pk=3)
        self.assertEqual(get_display_decimal(offer.discount()), 0.00)

    def test_offer_discount(self):
        offer = Offer.objects.get(pk=1)
        self.assertEqual(get_display_decimal(offer.discount()), 10.00)

    def test_offer_description_from_product(self):
        offer = Offer.objects.get(pk=3)
        self.assertEqual(
            offer.description,
            offer.products.all().first().description.get("description", ""),
        )

    def test_offer_description(self):
        offer = Offer.objects.get(pk=4)
        self.assertEqual(offer.description, offer.offer_description)

    # def test_empty_name_single_product(self):
    # p1 = Product.objects.get(pk=1)
    # offer = Offer()
    # offer.products.add(p1)
    # offer.start_date = timezone.now()
    # offer.save()
    # p1 = Product.objects.get(pk=1)

    # self.assertEqual(p1.name, offer.name)
    #     raise NotImplementedError()

    # def test_empty_name_bundle(self):
    # TODO: Implement Test
    # p1 = Product.objects.get(pk=1)
    # p2 = Product.objects.get(pk=2)
    # offer = Offer()
    # offer.products.add(p1)
    # offer.products.add(p2)
    # offer.start_date = timezone.now()
    # offer.save()
    # p1 = Product.objects.get(pk=1)

    # self.assertEqual("Bundle: " + ", ".join([p1,p2]), offer.name)
    # raise NotImplementedError()

    def test_get_best_currency_bundle_success(self):
        offer_bundle = Offer.objects.get(pk=4)

        offer_bundle.products.add(Product.objects.get(pk=1))

        self.assertEqual(offer_bundle.get_best_currency(), "usd")

    def test_get_best_currency_single_success(self):
        offer = Offer.objects.get(pk=4)

        self.assertEqual(offer.get_best_currency("mxn"), "mxn")

    def test_get_best_currency_single_success_not_default(self):
        offer = Offer.objects.get(pk=4)

        self.assertEqual(offer.get_best_currency("usd"), "usd")

    def test_get_best_currency_bundle_fail(self):
        offer_bundle = Offer.objects.get(pk=4)
        offer_bundle.products.add(Product.objects.get(pk=1))

        self.assertEqual(offer_bundle.get_best_currency("jpy"), "usd")

    def test_get_best_currency_single_fail(self):
        offer = Offer.objects.get(pk=4)

        self.assertEqual(offer.get_best_currency("jpy"), "usd")

    def test_get_status_display_active(self):
        offer = Offer.objects.get(pk=1)
        offer.start_date = timezone.now() - timedelta(days=1)
        offer.end_date = timezone.now() + timedelta(days=4)
        offer.save()
        self.assertEqual(offer.get_status_display(), "Active")

    def test_get_status_display_scheduled(self):
        offer = Offer.objects.get(pk=1)
        offer.start_date = timezone.now() + timedelta(days=2)
        offer.end_date = None
        offer.save()
        self.assertEqual(offer.get_status_display(), "Scheduled")

    def test_get_status_display_expired(self):
        offer = Offer.objects.get(pk=1)
        offer.start_date = timezone.now() - timedelta(days=5)
        offer.end_date = timezone.now() - timedelta(days=1)
        offer.save()
        self.assertEqual(offer.get_status_display(), "Expired")

    def test_soft_delete_success(self):
        offer = Offer.objects.all().first()
        offer_count_before_deletion = Offer.objects.all().count()
        offer.delete()

        deleted_offer_difference = (
            Offer.objects.all().count() - Offer.not_deleted.count()
        )

        self.assertEqual(
            Offer.objects.all().count() - deleted_offer_difference,
            Offer.not_deleted.count(),
        )
        self.assertEqual(offer_count_before_deletion, Offer.objects.all().count())

    def test_get_offer_start_date_returns_now(self):
        today = timezone.now()
        offer = Offer.objects.all().first()
        offer.term_start_date = None
        offer.save()

        start_date = offer.get_offer_start_date(today)
        self.assertEqual(today, start_date)

        offer.term_start_date = today - timedelta(days=2)
        offer.save()

        start_date = offer.get_offer_start_date(today)
        self.assertEqual(today, start_date)

    def test_get_offer_start_date_returns_term_start_date(self):
        today = timezone.now()
        offer = Offer.objects.all().first()
        offer.term_start_date = today + timedelta(days=13)
        offer.save()

        start_date = offer.get_offer_start_date(today)
        self.assertEqual(offer.term_start_date, start_date)

    def test_get_offer_end_date_month(self):
        monthly_offer = Offer.objects.get(pk=6)
        today = timezone.now()

        end_date = monthly_offer.get_offer_end_date(today)
        self.assertEqual(
            end_date, get_future_date_months(today, monthly_offer.get_period_length())
        )

    def test_get_offer_end_date_days(self):
        monthly_offer = Offer.objects.get(pk=6)
        monthly_offer.term_details["period_length"] = 7
        monthly_offer.term_details["term_units"] = TermDetailUnits.DAY
        monthly_offer.save()
        today = timezone.now()

        end_date = monthly_offer.get_offer_end_date(today)
        self.assertEqual(
            end_date, get_future_date_days(today, monthly_offer.get_period_length())
        )

    def test_get_trial_end_date_returns_billing_start_date(self):
        today = timezone.now()
        monthly_offer = Offer.objects.get(pk=6)
        monthly_offer.billing_start_date = today + timedelta(days=10)
        monthly_offer.save()

        trial_end_date = monthly_offer.get_trial_end_date(today)
        self.assertEqual(
            monthly_offer.billing_start_date - timedelta(days=1), trial_end_date
        )

    def test_get_trial_end_date_retunrs_delta_of_trial_days(self):
        today = timezone.now()
        monthly_offer = Offer.objects.get(pk=6)

        trial_end_date = monthly_offer.get_trial_end_date(today)
        self.assertEqual(today, trial_end_date)

    def test_get_payment_start_date_trial_offset_billing_start_date(self):
        today = timezone.now()
        monthly_offer = Offer.objects.get(pk=6)
        monthly_offer.billing_start_date = today + timedelta(days=10)
        monthly_offer.save()

        trial_start_date = monthly_offer.get_payment_start_date_trial_offset(today)
        self.assertEqual(monthly_offer.billing_start_date, trial_start_date)

    def test_get_payment_start_date_trial_offset_delta_trial_days(self):
        today = timezone.now()
        monthly_offer = Offer.objects.get(pk=6)
        monthly_offer.term_details["trial_days"] = 10
        monthly_offer.save()

        first_payment_date = monthly_offer.get_payment_start_date_trial_offset(today)
        self.assertEqual(
            today
            + timedelta(days=1)
            + timedelta(days=monthly_offer.term_details["trial_days"]),
            first_payment_date,
        )

    def test_has_any_discount_or_trial_true_has_discount(self):
        offer = Offer.objects.get(pk=6)
        offer.term_details["trial_amount"] = 10
        offer.save()

        self.assertTrue(offer.has_any_discount_or_trial())

    def test_has_any_discount_or_trial_true_has_trial_days(self):
        offer = Offer.objects.get(pk=6)
        offer.term_details["trial_days"] = 10
        offer.save()

        self.assertTrue(offer.has_any_discount_or_trial())

    def test_has_any_discount_or_trial_true_has_billing_start_date(self):
        today = timezone.now()
        offer = Offer.objects.get(pk=6)
        offer.billing_start_date = today + timedelta(days=10)
        offer.save()

        self.assertTrue(offer.has_any_discount_or_trial())

    def test_has_any_discount_or_trial_false(self):
        offer = Offer.objects.get(pk=6)
        offer.save()

        self.assertFalse(offer.has_any_discount_or_trial())


class ViewOfferTests(TestCase):

    fixtures = ["user", "unit_test"]

    def setUp(self):
        self.product = Product.objects.get(pk=1)

        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)

        self.mug_offer = Offer.objects.get(pk=4)
        self.shirt_offer = Offer.objects.get(pk=1)

        self.offers_list_uri = reverse("vendor_admin:manager-offer-list")
        self.offer_create_uri = reverse("vendor_admin:manager-offer-create")
        self.offer_update_uri = reverse(
            "vendor_admin:manager-offer-update", kwargs={"uuid": self.mug_offer.uuid}
        )

    def test_offers_list_status_code_success(self):
        response = self.client.get(self.offers_list_uri)

        self.assertEqual(response.status_code, 200)

    def test_offers_list_status_code_fail_no_login(self):
        client = Client()
        response = client.get(self.offers_list_uri)

        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_offers_list_has_content(self):
        response = self.client.get(self.offers_list_uri)

        self.assertContains(response, self.mug_offer.name)

    def test_offers_list_has_no_content(self):
        Offer.objects.all().delete()

        response = self.client.get(self.offers_list_uri)

        self.assertContains(response, "No Offers")

    def test_offers_list_has_create_offer(self):
        response = self.client.get(self.offers_list_uri)

        self.assertContains(response, self.offer_create_uri)

    def test_offers_list_has_update_offer(self):
        response = self.client.get(self.offers_list_uri)

        self.assertContains(response, self.offer_update_uri)

    def test_offer_create_status_code_success(self):
        response = self.client.get(self.offer_create_uri)

        self.assertEqual(response.status_code, 200)

    def test_offer_create_status_code_fail_no_login(self):
        client = Client()
        response = client.get(self.offer_create_uri)

        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_offer_update_status_code_success(self):
        response = self.client.get(self.offer_update_uri)

        self.assertEqual(response.status_code, 200)

    def test_offer_update_status_code_fail_no_login(self):
        client = Client()
        response = client.get(self.offer_update_uri)

        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_check_add_cart_link_status_code_post(self):
        url = self.mug_offer.add_to_cart_link()

        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("vendor:cart"))

    def test_check_remove_from_cart_link_request_post(self):
        url = self.shirt_offer.remove_from_cart_link()

        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("vendor:cart"))

    def test_check_add_cart_link_status_code_get(self):
        url = self.mug_offer.add_to_cart_link()

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("vendor:cart"))

    # def test_view_only_available_offers(self):
    #     raise NotImplementedError()

    # def test_view_show_only_available_products_to_add_to_offer(self):
    #     raise NotImplementedError()

    # def test_valid_add_to_cart_offer(self):
    #     raise NotImplementedError()

    # def test_valid_remove_to_cart_offer(self):
    #     raise NotImplementedError()

    # def test_create_profile_invoice_order_item_add_offer(self):
    #     raise NotImplementedError()

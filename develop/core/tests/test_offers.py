from core.models import Product

from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from vendor.models import Offer
from vendor.utils import get_display_decimal


User = get_user_model()


class ModelOfferTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        pass

    def test_create_offer(self):
        offer = Offer()
        offer.name = 'test-offer'
        offer.start_date = timezone.now()
        offer.save()
        offer.products.add(Product.objects.all().first())
        pass

    def test_default_site_id(self):
        offer = Offer()
        offer.name = 'test-offer'
        offer.start_date = timezone.now()
        offer.save()
        offer.products.add(Product.objects.all().first())

        self.assertEquals(Site.objects.get_current(), offer.site)

    def test_add_offer_to_cart_slug(self):
        mug_offer = Offer.objects.get(pk=4)
        slug = mug_offer.add_to_cart_link()
        self.assertEquals(slug, '/sales/cart/add/' + mug_offer.slug + '/')

    def test_remove_offer_to_cart_slug(self):
        mug_offer = Offer.objects.get(pk=4)
        slug = mug_offer.remove_from_cart_link()
        self.assertEquals(slug, '/sales/cart/remove/' + mug_offer.slug + '/')

    def test_get_current_price_is_msrp(self):
        offer = Offer.objects.get(pk=4)
        price = offer.current_price('mxn')
        self.assertEquals(price, 21.12)

    def test_get_current_price_is_msrp_default(self):
        offer = Offer.objects.get(pk=4)
        price = offer.current_price()
        self.assertEquals(price, 25.2)

    def test_get_current_price_has_only_start_date(self):
        offer = Offer.objects.get(pk=2)
        self.assertEquals(offer.current_price(), 75.0)

    def test_get_current_price_is_between_start_end_date(self):
        offer = Offer.objects.get(pk=3)
        self.assertEquals(offer.current_price(), 25.2)

    def test_get_current_price_acording_to_priority(self):
        offer = Offer.objects.get(pk=3)
        self.assertEquals(offer.current_price(), 25.2)

    def test_offer_negative_discount(self):
        offer = Offer.objects.get(pk=3)
        self.assertEquals(get_display_decimal(offer.discount()), 0.00)

    def test_offer_discount(self):
        offer = Offer.objects.get(pk=1)
        self.assertEquals(get_display_decimal(offer.discount()), 10.00)

    def test_offer_description_from_product(self):
        offer = Offer.objects.get(pk=3)
        self.assertEquals(offer.description, offer.products.all().first().description)

    def test_offer_description(self):
        offer = Offer.objects.get(pk=4)
        self.assertEquals(offer.description, offer.offer_description)

    # def test_empty_name_single_product(self):
        # p1 = Product.objects.get(pk=1)
        # offer = Offer()
        # offer.products.add(p1)
        # offer.start_date = timezone.now()
        # offer.save()
        # p1 = Product.objects.get(pk=1)

        # self.assertEquals(p1.name, offer.name)
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

        # self.assertEquals("Bundle: " + ", ".join([p1,p2]), offer.name)
        # raise NotImplementedError()

    def test_get_best_currency_bundle_success(self):
        offer_bundle = Offer.objects.get(pk=4)

        offer_bundle.products.add(Product.objects.get(pk=1))

        self.assertEquals(offer_bundle.get_best_currency(), 'usd')

    def test_get_best_currency_single_success(self):
        offer = Offer.objects.get(pk=4)

        self.assertEquals(offer.get_best_currency('mxn'), 'mxn')

    def test_get_best_currency_single_success_not_default(self):
        offer = Offer.objects.get(pk=4)

        self.assertEquals(offer.get_best_currency('usd'), 'usd')

    def test_get_best_currency_bundle_fail(self):
        offer_bundle = Offer.objects.get(pk=4)
        offer_bundle.products.add(Product.objects.get(pk=1))

        self.assertEquals(offer_bundle.get_best_currency('jpy'), 'usd')

    def test_get_best_currency_single_fail(self):
        offer = Offer.objects.get(pk=4)

        self.assertEquals(offer.get_best_currency('jpy'), 'usd')

    def test_get_status_display_active(self):
        offer = Offer.objects.get(pk=1)
        offer.start_date = (timezone.now() - timedelta(days=1))
        offer.end_date = (timezone.now() + timedelta(days=4))
        offer.save()
        self.assertEqual(offer.get_status_display(), "Active")

    def test_get_status_display_scheduled(self):
        offer = Offer.objects.get(pk=1)
        offer.start_date = (timezone.now() + timedelta(days=2))
        offer.end_date = None
        offer.save()
        self.assertEqual(offer.get_status_display(), "Scheduled")

    def test_get_status_display_expired(self):
        offer = Offer.objects.get(pk=1)
        offer.start_date = (timezone.now() - timedelta(days=5))
        offer.end_date = (timezone.now() - timedelta(days=1))
        offer.save()
        self.assertEqual(offer.get_status_display(), "Expired")

    def test_soft_delete_success(self):
        offer = Offer.objects.all().first()
        offer_count_before_deletion = Offer.objects.all().count()
        offer.delete()

        deleted_offer_difference = Offer.objects.all().count() - Offer.not_deleted.count()

        self.assertEqual(Offer.objects.all().count() - deleted_offer_difference, Offer.not_deleted.count())
        self.assertEquals(offer_count_before_deletion, Offer.objects.all().count())



class ViewOfferTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.product = Product.objects.get(pk=1)

        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)

        self.mug_offer = Offer.objects.get(pk=4)
        self.shirt_offer = Offer.objects.get(pk=1)

        self.offers_list_uri = reverse('vendor_admin:manager-offer-list')
        self.offer_create_uri = reverse('vendor_admin:manager-offer-create')
        self.offer_update_uri = reverse('vendor_admin:manager-offer-update', kwargs={'uuid': self.mug_offer.uuid})

    def test_offers_list_status_code_success(self):
        response = self.client.get(self.offers_list_uri)

        self.assertEquals(response.status_code, 200)

    def test_offers_list_status_code_fail_no_login(self):
        client = Client()
        response = client.get(self.offers_list_uri)

        self.assertEquals(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_offers_list_has_content(self):
        response = self.client.get(self.offers_list_uri)

        self.assertContains(response, self.mug_offer.name)

    def test_offers_list_has_no_content(self):
        Offer.objects.all().delete()

        response = self.client.get(self.offers_list_uri)

        self.assertContains(response, 'No Offers')

    def test_offers_list_has_create_offer(self):
        response = self.client.get(self.offers_list_uri)

        self.assertContains(response, self.offer_create_uri)

    def test_offers_list_has_update_offer(self):
        response = self.client.get(self.offers_list_uri)

        self.assertContains(response, self.offer_update_uri)

    def test_offer_create_status_code_success(self):
        response = self.client.get(self.offer_create_uri)

        self.assertEquals(response.status_code, 200)

    def test_offer_create_status_code_fail_no_login(self):
        client = Client()
        response = client.get(self.offer_create_uri)

        self.assertEquals(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_offer_update_status_code_success(self):
        response = self.client.get(self.offer_update_uri)

        self.assertEquals(response.status_code, 200)

    def test_offer_update_status_code_fail_no_login(self):
        client = Client()
        response = client.get(self.offer_update_uri)

        self.assertEquals(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_check_add_cart_link_status_code(self):
        url = self.mug_offer.add_to_cart_link()

        response = self.client.post(url)

        self.assertEquals(response.status_code, 302)
        self.assertEquals(response.url, reverse('vendor:cart'))

    def test_check_remove_from_cart_link_request(self):
        url = self.shirt_offer.remove_from_cart_link()

        response = self.client.post(url)

        self.assertEquals(response.status_code, 302)
        self.assertEquals(response.url, reverse('vendor:cart'))

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

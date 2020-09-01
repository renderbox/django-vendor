from django.contrib.auth.models import User  #TODO: CHANGE TO GET_USER_MODEL
from django.contrib.sites.models import Site
from django.test import TestCase, Client
from django.urls import reverse

from core.models import Product
from vendor.models import Offer, Price, OrderItem


class ModelOfferTests(TestCase):

    fixtures = ['unittest']

    def setUp(self):
        pass

    def test_create_offer(self):
        offer = Offer()
        offer.name = 'test-offer'
        offer.product = Product.objects.all().first()

    def test_change_offer_to_unavailable_product_change_to_unavailable(self):
        # TODO: Implement Tests
        pass

    def test_save_fail_product_not_available(self):
        # TODO: Implement Tests
        pass

    def test_save_fail_no_price_set(self):
        # TODO: Implement Tests
        pass

    def test_add_offer_to_cart_slug(self):
        mug_offer = Offer.objects.get(pk=4)
        slug = mug_offer.add_to_cart_link()
        self.assertEquals(slug,'/sales/cart/add/' + mug_offer.slug + '/')

    def test_remove_offer_to_cart_slug(self):
        mug_offer = Offer.objects.get(pk=4)
        slug = mug_offer.remove_from_cart_link()
        self.assertEquals(slug,'/sales/cart/remove/' + mug_offer.slug + '/')
    
    def test_get_current_price_is_msrp(self):
        offer = Offer.objects.get(pk=4)
        price = offer.current_price()
        self.assertEquals(price, 21.12)

    def test_get_current_price_has_only_start_date(self):
        offer = Offer.objects.get(pk=2)
        self.assertEquals(offer.current_price(), 75.0)

    def test_get_current_price_is_between_start_end_date(self):
        offer = Offer.objects.get(pk=3)
        self.assertEquals(offer.current_price(), 25.2)
    
    def test_get_current_price_acording_to_priority(self):
        offer = Offer.objects.get(pk=3)
        self.assertEquals(offer.current_price(), 25.2)
    

class ViewOfferTests(TestCase):
    
    fixtures = ['unittest']
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)

        self.mug_offer = Offer.objects.get(pk=4)
        self.shirt_offer = Offer.objects.get(pk=1)

    def test_check_add_cart_link_status_code(self):
        url = self.mug_offer.add_to_cart_link()

        response = self.client.get(url)

        self.assertEquals(response.status_code, 302)
        self.assertEquals(response.url, reverse('vendor:cart'))
        
    
    def test_check_remove_from_cart_link_request(self):
        url = self.shirt_offer.remove_from_cart_link()

        response = self.client.get(url)

        self.assertEquals(response.status_code, 302)
        self.assertEquals(response.url, reverse('vendor:cart'))
    

    def test_view_only_available_offers(self):
        # TODO: Implement Tests
        pass

    def test_view_show_only_available_products_to_add_to_offer(self):
        # TODO: Implement Tests
        pass

    def test_valid_add_to_cart_offer(self):
        # TODO: Implement Tests
        pass

    def test_valid_remove_to_cart_offer(self):
        # TODO: Implement Tests
        pass
    
    def test_create_profile_invoice_order_item_add_offer(self):
        
        pass

    
    
from core.models import Product

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, Client
from django.urls import reverse

from vendor.models import generate_sku, validate_msrp_format, validate_msrp
from vendor.models import Offer

User = get_user_model()

class ModelProductTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.new_product = Product()

    def test_create_product(self):
        self.new_product.sku = generate_sku()
        self.new_product.name = "Chocolate Chips"
        self.new_product.available = True

        self.new_product.save()

        self.assertTrue(self.new_product.pk)
        
    def test_unique_sku(self):
        product_a = Product()
        product_a.name = 'a'
        product_a.sku = 'a'
        product_a.save()

        product_b = Product()
        product_b.name = 'a'
        product_b.sku = 'a'
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                product_b.save()

    def test_unique_slug(self):
        product_a = Product()
        product_a.name = "a"
        product_a.save()

        product_b = Product()
        product_b.name = product_a.name
        product_b.site = Site.objects.get(pk=2)
        product_b.save()

        product_c = Product()
        product_c.name = product_a.name
        product_c.save()

        self.assertNotEqual(product_a.slug, product_c.slug)
        self.assertEqual(product_a.slug, product_b.slug)

    def test_valid_msrp(self):
        msrp =  "JPY,10.99"
        
        self.assertIsNone(validate_msrp_format(msrp))
        
    
    def test_raise_error_invalid_country_code_msrp(self):
        msrp = "JP,10.00"
        with self.assertRaises(ValidationError):
            validate_msrp_format(msrp)

    def test_raise_error_no_price_on_msrp(self):
        msrp = "MXN,"
        with self.assertRaises(ValidationError):
            validate_msrp_format(msrp)

    def test_raise_error_no_country_on_msrp(self):
        msrp = ",10.00"
        with self.assertRaises(ValidationError):
            validate_msrp_format(msrp)
    
    def test_raise_error_only_comma_msrp(self):
        msrp = ","
        with self.assertRaises(ValidationError):
            validate_msrp_format(msrp)
    
    def test_get_best_currency_success(self):
        product = Product.objects.get(pk=1)
        
        self.assertEquals(product.get_best_currency(), 'usd')

    def test_get_best_currency_fail(self):
        product = Product.objects.get(pk=1)
        
        self.assertEquals(product.get_best_currency('mxn'), 'usd')

    def test_create_product_valid_msrp(self):
        self.assertIsNone(validate_msrp({'msrp': {'default': 'usd', 'usd': 20 }}))

    def test_create_product_valid_msrp_multiple_currencies(self):
        self.assertIsNone(validate_msrp({'msrp': {'default': 'usd', 'usd': 20, 'jpy': 12 }}))

    def test_create_product_in_valid_msrp(self):
        with self.assertRaises(ValidationError):
            validate_msrp({'msrp': {'default': 'rub', 'rub': 20 }})

    def test_create_product_in_valid_msrp(self):
        with self.assertRaises(ValidationError):
            validate_msrp({'msrp': {'default': 'usd', 'usd': 21, 'rub': 20 }})


class TransactionProductTests(TestCase):

    def setUp(self):
        pass

    # def test_transaction_csv_add_product(self):
    #     raise NotImplementedError()

    # def test_transaction_csv_edit_product(self):
    #     raise NotImplementedError()


class ViewsProductTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.product = Product.objects.get(pk=1)

        self.products_list_uri = reverse('vendor_admin:manager-product-list')
        self.product_create_uri = reverse('vendor_admin:manager-product-create')
        self.product_update_uri = reverse('vendor_admin:manager-product-update', kwargs={'uuid': self.product.uuid})


        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)

    def test_products_list_status_code_success(self):
        response = self.client.get(self.products_list_uri)

        self.assertEquals(response.status_code, 200)

    def test_products_list_status_code_fail_no_login(self):
        client = Client()
        response = client.get(self.products_list_uri)

        self.assertEquals(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_products_list_has_no_content(self):
        Product.objects.all().delete()
        
        response = self.client.get(self.products_list_uri)

        self.assertContains(response, 'No Products')

    def test_products_list_has_content(self):
        response = self.client.get(self.products_list_uri)

        self.assertContains(response, self.product.name)

    def test_products_list_has_create_product(self):
        response = self.client.get(self.products_list_uri)

        self.assertContains(response, self.product_create_uri)

    def test_products_list_has_update_product(self):
        response = self.client.get(self.products_list_uri)

        self.assertContains(response, self.product_update_uri)

    def test_product_create_status_code_success(self):
        response = self.client.get(self.product_create_uri)

        self.assertEquals(response.status_code, 200)

    def test_products_create_status_code_fail_no_login(self):
        client = Client()
        response = client.get(self.product_create_uri)

        self.assertEquals(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_product_update_status_code_success(self):
        response = self.client.get(self.product_update_uri)

        self.assertEquals(response.status_code, 200)

    def test_products_update_status_code_fail_no_login(self):
        client = Client()
        response = client.get(self.product_update_uri)

        self.assertEquals(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_product_availability_toggle_activate(self):
        uri = reverse('vendor_admin:manager-product-availablility', kwargs={'uuid': self.product.uuid})

        self.product.available = False
        self.product.save()

        for offer in Offer.objects.filter(products__in=[self.product]):
            offer.available = False
            offer.save()

        response = self.client.post(uri, data={'available': True})
        self.product.refresh_from_db()
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.product.available)
        self.assertTrue(all((offer.available for offer in Offer.objects.filter(products__in=[self.product]))))
    
    def test_product_availability_toggle_inactivate(self):
        uri = reverse('vendor_admin:manager-product-availablility', kwargs={'uuid': self.product.uuid})

        self.product.available = True
        self.product.save()

        for offer in Offer.objects.filter(products__in=[self.product]):
            offer.available = True
            offer.save()

        response = self.client.post(uri, data={'available': False})
        self.product.refresh_from_db()
        
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.product.available)
        self.assertFalse(all((offer.available for offer in Offer.objects.filter(products__in=[self.product]))))


    # def test_view_uplaod_csv_product(self):
    #     raise NotImplementedError()

    # def test_view_downlaod_csv_product(self):
    #     raise NotImplementedError()

    # def test_view_warning_change_product_to_unavailable(self):
    #     raise NotImplementedError()

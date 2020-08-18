from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test import TestCase, Client
from django.urls import reverse

from vendor.models import generate_sku

from core.models import Product



class ModelProductTests(TestCase):

    fixtures = ['site', 'product']

    def test_create_product(self):
        product = Product()
        product.sku = generate_sku()
        product.name = "Chocolate Chips"
        product.available = True

        product.save()

        self.assertTrue(product.pk)

    # TODO: Ask if the slug should be unique only inside a Site or for all sites
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

    # TODO: Ask if SKU has to be unique inside a Site or across all Sites. 
    def test_generate_unique_sku(self):
        raise NotImplementedError

class ClientProductTests(TestCase):

    fixtures = ['site', 'user', 'product']

    def setUp(self):
        pass

    def test_client_add_product(self):
        raise NotImplementedError

    def test_client_edit_product(self):
        raise NotImplementedError

    def test_client_delete_product(self):
        raise NotImplementedError
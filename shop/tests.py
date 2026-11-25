from django.test import TestCase
from django.urls import reverse

from .factories import make_category, make_product


class CatalogTests(TestCase):
    def setUp(self):
        self.category = make_category()
        self.product = make_product(name='FIFA 25', category=self.category)

    def test_product_list(self):
        response = self.client.get(reverse('shop:product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'FIFA 25')

    def test_category_page(self):
        response = self.client.get(self.category.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'FIFA 25')

    def test_product_detail(self):
        response = self.client.get(self.product.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'FIFA 25')


class CartTests(TestCase):
    def setUp(self):
        self.product = make_product(name='FIFA 25', stock=5)

    def test_add_and_remove(self):
        self.client.post(reverse('shop:cart_add', args=[self.product.pk]), {'quantity': 2})
        self.assertContains(self.client.get(reverse('shop:cart_detail')), 'FIFA 25')
        self.client.get(reverse('shop:cart_remove', args=[self.product.pk]))
        self.assertNotContains(self.client.get(reverse('shop:cart_detail')), 'FIFA 25')

    def test_empty_cart_page(self):
        self.assertEqual(self.client.get(reverse('shop:cart_detail')).status_code, 200)
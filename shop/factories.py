from decimal import Decimal

from django.utils.text import slugify

from .models import Category, Product


def make_category(name='PlayStation 5'):
    category, _ = Category.objects.get_or_create(name=name, defaults={'slug': slugify(name)})
    return category


def make_product(name='Test Game', price='100.00', stock=5, category=None):
    return Product.objects.create(
        category=category or make_category(), name=name, slug=slugify(name),
        description='Опис', price=Decimal(price), stock=stock, is_active=True)
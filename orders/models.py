from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

from shop.models import Product

CENT = Decimal('0.01')


class Coupon(models.Model):
    code = models.CharField('Промокод', max_length=50, unique=True)
    discount_percent = models.PositiveIntegerField(
        'Знижка, %', validators=[MinValueValidator(1), MaxValueValidator(100)])
    valid_from = models.DateTimeField('Діє з')
    valid_to = models.DateTimeField('Діє до')
    max_uses = models.PositiveIntegerField('Макс. використань', default=100)
    used_count = models.PositiveIntegerField('Використано разів', default=0, editable=False)
    active = models.BooleanField('Активний', default=True)

    class Meta:
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоди'

    def __str__(self):
        return f'{self.code} (-{self.discount_percent}%)'

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def get_error(self):
        """Возвращает None, если купон можно применить, иначе текст ошибки."""
        now = timezone.now()
        if not self.active:
            return 'Промокод вимкнено.'
        if now < self.valid_from:
            return 'Промокод ще не почав діяти.'
        if now > self.valid_to:
            return 'Термін дії промокоду минув.'
        if self.used_count >= self.max_uses:
            return 'Ліміт використань промокоду вичерпано.'
        return None

    def is_valid(self):
        return self.check() is None


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Новий'
        PAID = 'paid', 'Оплачений'
        SHIPPED = 'shipped', 'Відправлений'
        DELIVERED = 'delivered', 'Доставлений'
        CANCELLED = 'cancelled', 'Скасований'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name='orders', verbose_name='Користувач')
    email = models.EmailField('Email')
    status = models.CharField('Статус', max_length=20, choices=Status.choices, default=Status.NEW)
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='orders', verbose_name='Промокод')
    discount_percent = models.PositiveIntegerField('Знижка, %', default=0)
    created_at = models.DateTimeField('Створено', auto_now_add=True)
    updated_at = models.DateTimeField('Оновлено', auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Замовлення'
        verbose_name_plural = 'Замовлення'

    def __str__(self):
        return f'Замовлення №{self.pk}'

    def get_absolute_url(self):
        return reverse('orders:order_detail', args=[self.pk])

    def get_subtotal(self):
        return sum((item.get_cost() for item in self.items.all()), Decimal('0'))

    def get_discount(self):
        return (self.get_subtotal() * self.discount_percent / Decimal('100')).quantize(CENT, ROUND_HALF_UP)

    def get_total(self):
        return self.get_subtotal() - self.get_discount()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL, related_name='order_items')
    product_name = models.CharField('Назва', max_length=200)
    price = models.DecimalField('Ціна', max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField('Кількість', default=1)

    class Meta:
        verbose_name = 'Позиція замовлення'
        verbose_name_plural = 'Позиції замовлення'

    def __str__(self):
        return f'{self.product_name} × {self.quantity}'

    def get_cost(self):
        return self.price * self.quantity


class ShippingAddress(models.Model):
    order = models.OneToOneField(Order, related_name='shipping_address', on_delete=models.CASCADE)
    full_name = models.CharField('ПІБ отримувача', max_length=150)
    phone = models.CharField('Телефон', max_length=20)
    country = models.CharField('Країна', max_length=100, default='Україна')
    city = models.CharField('Місто', max_length=100)
    address = models.CharField('Адреса / відділення доставки', max_length=255)
    postal_code = models.CharField('Індекс', max_length=20, blank=True)

    class Meta:
        verbose_name = 'Адреса доставки'
        verbose_name_plural = 'Адреси доставки'

    def __str__(self):
        return f'{self.full_name}, {self.city}, {self.address}'
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('shop', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Coupon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50, unique=True, verbose_name='Промокод')),
                ('discount_percent', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(100)], verbose_name='Скидка, %')),
                ('valid_from', models.DateTimeField(verbose_name='Действует с')),
                ('valid_to', models.DateTimeField(verbose_name='Действует до')),
                ('max_uses', models.PositiveIntegerField(default=100, verbose_name='Макс. использований')),
                ('used_count', models.PositiveIntegerField(default=0, editable=False, verbose_name='Использован раз')),
                ('active', models.BooleanField(default=True, verbose_name='Активен')),
            ],
            options={'verbose_name': 'Промокод', 'verbose_name_plural': 'Промокоды'},
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, verbose_name='Email')),
                ('status', models.CharField(choices=[('new', 'Новый'), ('paid', 'Оплачен'), ('shipped', 'Отправлен'), ('delivered', 'Доставлен'), ('cancelled', 'Отменён')], default='new', max_length=20, verbose_name='Статус')),
                ('discount_percent', models.PositiveIntegerField(default=0, verbose_name='Скидка, %')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создан')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлён')),
                ('coupon', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to='orders.coupon', verbose_name='Промокод')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={'verbose_name': 'Заказ', 'verbose_name_plural': 'Заказы', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_name', models.CharField(max_length=200, verbose_name='Название')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Цена')),
                ('quantity', models.PositiveIntegerField(default=1, verbose_name='Количество')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='orders.order')),
                ('product', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order_items', to='shop.product')),
            ],
            options={'verbose_name': 'Позиция заказа', 'verbose_name_plural': 'Позиции заказа'},
        ),
        migrations.CreateModel(
            name='ShippingAddress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=150, verbose_name='ФИО получателя')),
                ('phone', models.CharField(max_length=20, verbose_name='Телефон')),
                ('country', models.CharField(default='Украина', max_length=100, verbose_name='Страна')),
                ('city', models.CharField(max_length=100, verbose_name='Город')),
                ('address', models.CharField(max_length=255, verbose_name='Адрес / отделение доставки')),
                ('postal_code', models.CharField(blank=True, max_length=20, verbose_name='Индекс')),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='shipping_address', to='orders.order')),
            ],
            options={'verbose_name': 'Адрес доставки', 'verbose_name_plural': 'Адреса доставки'},
        ),
    ]

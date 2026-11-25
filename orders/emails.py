import logging

from django.conf import settings
from django.core.mail import EmailMessage

from .invoices import build_invoice_pdf

logger = logging.getLogger(__name__)


def send_order_confirmation(order_id):
    """Отправляет подтверждение заказа с PDF-счётом. Ошибка почты не ломает оформление."""
    from .models import Order
    try:
        order = (Order.objects.select_related('coupon', 'shipping_address')
                 .prefetch_related('items').get(pk=order_id))
        msg = EmailMessage(
            subject=f'DiscZone: замовлення №{order.pk} прийнято',
            body=(f'Вітаємо!\n\nДякуємо за замовлення №{order.pk} у DiscZone.\n'
                  f'Сума до сплати: {order.get_total()} ₴.\nРахунок у вкладенні.\n'),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.email],
        )
        msg.attach(f'invoice_{order.pk}.pdf', build_invoice_pdf(order), 'application/pdf')
        msg.send()
    except Exception:
        logger.exception('Не удалось отправить письмо по заказу %s', order_id)
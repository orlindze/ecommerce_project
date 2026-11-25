from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from shop.cart import Cart
from shop.models import Product

from .emails import send_order_confirmation
from .forms import CouponApplyForm, ShippingAddressForm
from .invoices import build_invoice_pdf
from .models import CENT, Coupon, Order, OrderItem

COUPON_SESSION_ID = 'coupon_id'
ORDERS_SESSION_ID = 'order_ids'


class OrderError(Exception):
    pass


def _get_session_coupon(request):
    """Купон из сессии, если он всё ещё валиден; иначе чистим сессию."""
    coupon_id = request.session.get(COUPON_SESSION_ID)
    if not coupon_id:
        return None
    coupon = Coupon.objects.filter(pk=coupon_id).first()
    if coupon is None or coupon.check():
        request.session.pop(COUPON_SESSION_ID, None)
        return None
    return coupon


def _can_view(request, order):
    if request.user.is_staff:
        return True
    if request.user.is_authenticated and order.user_id == request.user.id:
        return True
    return order.pk in request.session.get(ORDERS_SESSION_ID, [])


def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.info(request, 'Кошик порожній.')
        return redirect('shop:cart_detail')

    coupon = _get_session_coupon(request)
    subtotal = cart.get_total_price()
    percent = coupon.discount_percent if coupon else 0
    discount = (subtotal * percent / Decimal('100')).quantize(CENT)
    context = {
        'cart': cart, 'coupon': coupon, 'subtotal': subtotal, 'discount': discount,
        'total': subtotal - discount, 'coupon_form': CouponApplyForm(),
    }

    if request.method == 'POST':
        form = ShippingAddressForm(request.POST)
        if form.is_valid():
            try:
                order = _create_order(request, cart, form, coupon)
            except OrderError as e:
                messages.error(request, str(e))
                return redirect('orders:checkout')
            transaction.on_commit(lambda: send_order_confirmation(order.pk))
            messages.success(request, f'Замовлення №{order.pk} оформлено. Рахунок надіслано на {order.email}.')
            return redirect(order)
    else:
        initial = {}
        if request.user.is_authenticated:
            initial = {'email': request.user.email,
                       'full_name': request.user.get_full_name(),
                       'phone': request.user.phone or ''}
            profile = getattr(request.user, 'profile', None)
            if profile:
                initial['address'] = profile.address
        form = ShippingAddressForm(initial=initial)
    context['form'] = form
    return render(request, 'orders/checkout.html', context)


@transaction.atomic
def _create_order(request, cart, form, coupon):
    """Создаёт заказ, списывает остатки и использование купона атомарно."""
    order = Order(email=form.cleaned_data['email'],
                  user=request.user if request.user.is_authenticated else None)

    if coupon:
        # Условное обновление: два одновременных заказа не превысят max_uses.
        updated = Coupon.objects.filter(pk=coupon.pk, active=True, used_count__lt=F('max_uses')) \
            .update(used_count=F('used_count') + 1)
        if not updated:
            request.session.pop(COUPON_SESSION_ID, None)
            raise OrderError('Промокод більше не можна використати. Перевірте суму та оформіть замовлення знову.')
        order.coupon = coupon
        order.discount_percent = coupon.discount_percent
    order.save()

    for item in cart:
        product = item['product']
        qty = item['quantity']
        # Остаток списываем атомарно и только если его хватает.
        ok = Product.objects.filter(pk=product.pk, is_active=True, stock__gte=qty) \
            .update(stock=F('stock') - qty)
        if not ok:
            raise OrderError(f'Недостатньо «{product.name}» на складі.')
        OrderItem.objects.create(order=order, product=product, product_name=product.name,
                                 price=product.price, quantity=qty)

    address = form.save(commit=False)
    address.order = order
    address.save()

    cart.clear()
    request.session.pop(COUPON_SESSION_ID, None)
    request.session[ORDERS_SESSION_ID] = request.session.get(ORDERS_SESSION_ID, []) + [order.pk]
    return order


@require_POST
def coupon_apply(request):
    form = CouponApplyForm(request.POST)
    if form.is_valid():
        coupon = Coupon.objects.filter(code__iexact=form.cleaned_data['code']).first()
        if coupon is None:
            messages.error(request, 'Такого промокоду не існує.')
        elif (error := coupon.check()):
            messages.error(request, error)
        else:
            request.session[COUPON_SESSION_ID] = coupon.pk
            messages.success(request, f'Промокод {coupon.code} застосовано: −{coupon.discount_percent}%.')
    else:
        messages.error(request, 'Введіть промокод.')
    return redirect('orders:checkout')


@require_POST
def coupon_remove(request):
    request.session.pop(COUPON_SESSION_ID, None)
    return redirect('orders:checkout')


@login_required
def order_list(request):
    orders = request.user.orders.prefetch_related('items')
    return render(request, 'orders/order_list.html', {'orders': orders})


def order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related('coupon', 'shipping_address')
                              .prefetch_related('items'), pk=pk)
    if not _can_view(request, order):
        return redirect('login')
    return render(request, 'orders/order_detail.html', {'order': order})


def order_invoice(request, pk):
    order = get_object_or_404(Order.objects.select_related('coupon', 'shipping_address')
                              .prefetch_related('items'), pk=pk)
    if not _can_view(request, order):
        return redirect('login')
    response = HttpResponse(build_invoice_pdf(order), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.pk}.pdf"'
    return response
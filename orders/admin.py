from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse

from .models import Coupon, Order, OrderItem, ShippingAddress


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    raw_id_fields = ('product',)


class ShippingAddressInline(admin.StackedInline):
    model = ShippingAddress
    extra = 0
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'status', 'coupon', 'total', 'created_at', 'invoice_link')
    list_filter = ('status', 'created_at', 'coupon')
    search_fields = ('id', 'email', 'shipping_address__full_name', 'shipping_address__phone')
    list_editable = ('status',)
    readonly_fields = ('created_at', 'updated_at', 'discount_percent')
    inlines = [ShippingAddressInline, OrderItemInline]
    actions = ['mark_paid', 'mark_shipped']
    list_select_related = ('coupon',)

    @admin.display(description='Разом, ₴')
    def total(self, obj):
        return obj.get_total()

    @admin.display(description='Рахунок')
    def invoice_link(self, obj):
        return format_html('<a href="{}">PDF</a>', reverse('orders:order_invoice', args=[obj.pk]))

    @admin.action(description='Позначити як оплачені')
    def mark_paid(self, request, queryset):
        n = queryset.update(status=Order.Status.PAID)
        self.message_user(request, f'Оновлено замовлень: {n}', messages.SUCCESS)

    @admin.action(description='Позначити як відправлені')
    def mark_shipped(self, request, queryset):
        n = queryset.update(status=Order.Status.SHIPPED)
        self.message_user(request, f'Оновлено замовлень: {n}', messages.SUCCESS)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'valid_from', 'valid_to', 'used_count', 'max_uses', 'active')
    list_filter = ('active', 'valid_to')
    search_fields = ('code',)
    list_editable = ('active',)
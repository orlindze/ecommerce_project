from django import forms

from .models import ShippingAddress


class ShippingAddressForm(forms.ModelForm):
    email = forms.EmailField(label='Email (для підтвердження та рахунку)')

    class Meta:
        model = ShippingAddress
        fields = ['full_name', 'phone', 'country', 'city', 'address', 'postal_code']


class CouponApplyForm(forms.Form):
    code = forms.CharField(label='Промокод', max_length=50)

    def clean_code(self):
        return self.cleaned_data['code'].strip().upper()
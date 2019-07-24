from django import forms

from .models import *


class AddToCartForm(forms.ModelForm):
    # quantity = forms.ChoiceField(widget=forms.Select, choices=)

    class Meta:
        model = ProductCart
        fields = ["quantity"]



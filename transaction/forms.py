import re

from django import forms
from django.core.exceptions import ValidationError

from .models import CATEGORY_CHOICES, KIND_CHOICES, Budget, Transaction
from .validation import clean_description, validate_category_for_kind, validate_date


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['kind', 'amount', 'category', 'date', 'description']
        widgets = {
            'kind': forms.RadioSelect(attrs={'class': 'kind-radio'}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'inputmode': 'decimal',
                                               'placeholder': '0.00'}),
            'category': forms.Select(attrs={'data-category-select': ''}),
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'description': forms.TextInput(attrs={'placeholder': 'e.g. Semester textbooks',
                                                  'maxlength': 140}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['kind'].choices = KIND_CHOICES  # no empty "-----" radio button

    def clean_date(self):
        return validate_date(self.cleaned_data['date'])

    def clean_description(self):
        return clean_description(self.cleaned_data.get('description'))

    def clean(self):
        cleaned = super().clean()
        kind, category = cleaned.get('kind'), cleaned.get('category')
        if kind and category:
            try:
                validate_category_for_kind(kind, category)
            except ValidationError as exc:
                for field, errors in exc.message_dict.items():
                    self.add_error(field, errors)
        return cleaned


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['category', 'monthly_limit']
        widgets = {
            'monthly_limit': forms.NumberInput(attrs={'step': '1', 'min': '1', 'inputmode': 'decimal'}),
        }
        labels = {'monthly_limit': 'Monthly limit'}

    def validate_unique(self):
        # The view saves with update_or_create (one budget per category), so skip the
        # unique (user, category) check; `user` is not a form field anyway.
        pass


_MONTH = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')


class TransactionFilterForm(forms.Form):
    """Validates the query-string filters on the transactions page."""

    q = forms.CharField(required=False, max_length=60, label='Search')
    kind = forms.ChoiceField(required=False, choices=[('', 'All types')] + KIND_CHOICES)
    category = forms.ChoiceField(required=False, choices=[('', 'All categories')] + CATEGORY_CHOICES)
    month = forms.CharField(required=False, max_length=7,
                            widget=forms.TextInput(attrs={'type': 'month'}))

    def clean_month(self):
        month = self.cleaned_data.get('month', '').strip()
        if month and not _MONTH.match(month):
            raise ValidationError('Use the format YYYY-MM.')
        return month

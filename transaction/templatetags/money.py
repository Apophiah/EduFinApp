from decimal import Decimal, InvalidOperation

from django import template
from django.conf import settings

register = template.Library()


@register.filter
def money(value, signed=False):
    """Format an amount as 'RWF 12,500' (decimals only when they are not zero)."""
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return value
    sign = ''
    if amount < 0:
        sign = '-'
    elif signed and amount > 0:
        sign = '+'
    amount = abs(amount)
    text = f'{amount:,.2f}'
    if text.endswith('.00'):
        text = text[:-3]
    return f'{sign}{settings.CURRENCY} {text}'


@register.filter
def short_money(value):
    """Compact amount for chart axes: 1.2k, 3.4M."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return value
    for limit, suffix in ((1e6, 'M'), (1e3, 'k')):
        if abs(amount) >= limit:
            return f'{amount / limit:.1f}'.rstrip('0').rstrip('.') + suffix
    return f'{amount:.0f}'

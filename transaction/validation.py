"""Validation rules shared by the HTML forms and the REST API."""

import datetime
import re

from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import CATEGORIES_BY_KIND

EARLIEST_DATE = datetime.date(2000, 1, 1)
MAX_DAYS_AHEAD = 366
_CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def validate_category_for_kind(kind, category):
    allowed = CATEGORIES_BY_KIND.get(kind)
    if allowed is None:
        raise ValidationError({'kind': 'Choose income or expense.'})
    if category not in allowed:
        raise ValidationError({'category': f'This category cannot be used for {kind}.'})


def validate_date(value):
    latest = timezone.localdate() + datetime.timedelta(days=MAX_DAYS_AHEAD)
    if value < EARLIEST_DATE:
        raise ValidationError('Dates before 1 January 2000 are not allowed.')
    if value > latest:
        raise ValidationError('Dates more than a year in the future are not allowed.')
    return value


def clean_description(value):
    value = (value or '').strip()
    if _CONTROL_CHARS.search(value):
        raise ValidationError('The description contains characters that are not allowed.')
    return re.sub(r'\s+', ' ', value)

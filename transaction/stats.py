"""Numbers and chart geometry for the dashboard. Everything is scoped to one user."""

import datetime
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from .models import CATEGORY_LABELS, EXPENSE, INCOME, Budget, Transaction

# Colours for the expense donut (CSS classes seg-0 … seg-8 in app.css).
SEGMENTS = 9


def month_start(day):
    return day.replace(day=1)


def add_months(day, months):
    month_index = day.year * 12 + (day.month - 1) + months
    return datetime.date(month_index // 12, month_index % 12 + 1, 1)


def summary(user, today=None):
    today = today or timezone.localdate()
    qs = Transaction.objects.for_user(user)
    this_month = qs.filter(date__gte=month_start(today), date__lt=add_months(today, 1))

    total_income = qs.total(INCOME)
    total_expense = qs.total(EXPENSE)
    month_income = this_month.total(INCOME)
    month_expense = this_month.total(EXPENSE)
    savings_rate = None
    if month_income > 0:
        savings_rate = int(round((month_income - month_expense) / month_income * 100))

    return {
        'balance': total_income - total_expense,
        'month_income': month_income,
        'month_expense': month_expense,
        'month_net': month_income - month_expense,
        'savings_rate': savings_rate,
        'count': qs.count(),
        'month_label': today.strftime('%B %Y'),
    }


def monthly_bars(user, months=6, today=None):
    """Income vs expense per month, with SVG bar geometry (viewBox 0 0 600 240)."""
    today = today or timezone.localdate()
    first = add_months(month_start(today), -(months - 1))
    rows = (Transaction.objects.for_user(user)
            .filter(date__gte=first, date__lt=add_months(today, 1))
            .values('date__year', 'date__month', 'kind').annotate(total=Sum('amount')))
    totals = {}
    for row in rows:
        totals[(row['date__year'], row['date__month'], row['kind'])] = row['total']

    data = []
    for i in range(months):
        m = add_months(first, i)
        data.append({
            'label': m.strftime('%b'),
            'income': totals.get((m.year, m.month, INCOME), Decimal('0')),
            'expense': totals.get((m.year, m.month, EXPENSE), Decimal('0')),
        })

    peak = max([max(d['income'], d['expense']) for d in data] + [Decimal('1')])
    # Leave 48 units on the left for the y-axis labels.
    chart_h, base_y, left = 175, 200, 48
    slot = (600 - left) / months
    bar_w = min(28, slot / 3)
    for i, d in enumerate(data):
        center = left + slot * i + slot / 2
        for kind, offset in (('income', -bar_w - 2), ('expense', 2)):
            h = float(d[kind] / peak) * chart_h
            h = max(h, 2.0) if d[kind] > 0 else 0.0
            d[f'{kind}_x'] = round(center + offset, 1)
            d[f'{kind}_h'] = round(h, 1)
            d[f'{kind}_y'] = round(base_y - h, 1)
        d['label_x'] = round(center, 1)
    return {
        'months': data,
        'bar_w': round(bar_w, 1),
        'peak': peak,
        'has_data': any(d['income'] or d['expense'] for d in data),
        'gridlines': [{'y': round(base_y - chart_h * f, 1), 'value': peak * Decimal(str(f))}
                      for f in (0.25, 0.5, 0.75, 1.0)],
    }


def expense_breakdown(user, today=None):
    """This month's spending per category, as SVG donut segments (circumference = 100)."""
    today = today or timezone.localdate()
    rows = (Transaction.objects.for_user(user)
            .filter(kind=EXPENSE, date__gte=month_start(today), date__lt=add_months(today, 1))
            .values('category').annotate(total=Sum('amount')).order_by('-total'))
    rows = list(rows)
    grand = sum((r['total'] for r in rows), Decimal('0'))
    segments, cumulative = [], 0.0
    for i, r in enumerate(rows):
        pct = float(r['total'] / grand * 100) if grand else 0.0
        segments.append({
            'label': CATEGORY_LABELS.get(r['category'], r['category']),
            'total': r['total'],
            'pct': round(pct),
            'dash': f'{pct:.2f} {100 - pct:.2f}',
            # Start at 12 o'clock (offset 25) and go clockwise.
            'offset': f'{(25 - cumulative) % 100:.2f}',
            'color': i % SEGMENTS,
        })
        cumulative += pct
    return {'segments': segments, 'total': grand}


def budget_progress(user, today=None):
    today = today or timezone.localdate()
    spent = dict(
        Transaction.objects.for_user(user)
        .filter(kind=EXPENSE, date__gte=month_start(today), date__lt=add_months(today, 1))
        .values_list('category').annotate(total=Sum('amount'))
    )
    items = []
    for budget in Budget.objects.filter(user=user):
        used = spent.get(budget.category, Decimal('0'))
        pct = float(used / budget.monthly_limit * 100)
        items.append({
            'budget': budget,
            'spent': used,
            'left': budget.monthly_limit - used,
            'over_by': max(used - budget.monthly_limit, Decimal('0')),
            'pct': round(pct),
            'bar': round(min(pct, 100), 1),
            'state': 'over' if pct > 100 else ('warn' if pct >= 80 else 'ok'),
        })
    return items

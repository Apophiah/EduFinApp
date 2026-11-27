"""Create a demo student with six months of realistic transactions and budgets.

    python manage.py seed_demo

The password is random and printed once. Run again with --reset to start over.
"""

import datetime
import random
import secrets
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction
from django.utils import timezone

from transaction.models import Budget, Transaction
from transaction.stats import add_months, month_start

INCOME_PLAN = [
    ('allowance', 'Monthly allowance', 60000),
    ('scholarship', 'Bursary payment', 45000),
]
EXPENSE_PLAN = [
    ('rent', 'Hostel rent', 35000, 1),
    ('food', 'Groceries', 6500, 4),
    ('food', 'Lunch at campus', 1500, 6),
    ('transport', 'Moto to campus', 800, 8),
    ('data', 'Mobile data bundle', 5000, 1),
    ('books', 'Photocopies & notes', 2500, 1),
    ('fun', 'Movie night', 4000, 1),
    ('health', 'Pharmacy', 3000, 0),
]


class Command(BaseCommand):
    help = 'Create a demo user with sample transactions and budgets.'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='demo')
        parser.add_argument('--reset', action='store_true', help='Delete and recreate the demo user.')

    @db_transaction.atomic
    def handle(self, *args, username, reset, **options):
        User = get_user_model()
        existing = User.objects.filter(username=username).first()
        if existing and not reset:
            self.stdout.write(self.style.WARNING(f'User "{username}" already exists. Use --reset to recreate it.'))
            return
        if existing:
            existing.delete()

        password = secrets.token_urlsafe(12)
        user = User.objects.create_user(username=username, password=password, first_name='Aline',
                                        email=f'{username}@example.com')
        rng = random.Random(42)
        today = timezone.localdate()
        rows = []
        for back in range(5, -1, -1):
            start = add_months(month_start(today), -back)
            last_day = today.day if back == 0 else 28
            for category, desc, amount in INCOME_PLAN:
                rows.append(Transaction(user=user, kind='income', category=category, description=desc,
                                        amount=Decimal(amount), date=start))
            if back % 2 == 0:
                rows.append(Transaction(user=user, kind='income', category='job', description='Tutoring',
                                        amount=Decimal(rng.choice([15000, 20000, 25000])),
                                        date=start + datetime.timedelta(days=min(14, last_day - 1))))
            for category, desc, amount, times in EXPENSE_PLAN:
                count = times or rng.choice([0, 1])
                for _ in range(count):
                    day = rng.randint(1, max(1, last_day))
                    jitter = Decimal(rng.randint(-20, 30)) / 100
                    rows.append(Transaction(user=user, kind='expense', category=category, description=desc,
                                            amount=(Decimal(amount) * (1 + jitter)).quantize(Decimal('1')),
                                            date=start.replace(day=day)))
            if back in (0, 3):
                rows.append(Transaction(user=user, kind='expense', category='tuition',
                                        description='Registration fee', amount=Decimal('25000'),
                                        date=start.replace(day=min(5, last_day))))
        Transaction.objects.bulk_create(rows)
        for category, limit in (('food', 30000), ('transport', 8000), ('data', 5000), ('fun', 6000)):
            Budget.objects.create(user=user, category=category, monthly_limit=Decimal(limit))

        self.stdout.write(self.style.SUCCESS(f'Created "{username}" with {len(rows)} transactions.'))
        self.stdout.write(f'Password (shown once): {password}')

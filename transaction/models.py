from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

INCOME = 'income'
EXPENSE = 'expense'
KIND_CHOICES = [(INCOME, 'Income'), (EXPENSE, 'Expense')]

INCOME_CATEGORIES = [
    ('allowance', 'Allowance'),
    ('scholarship', 'Scholarship / bursary'),
    ('job', 'Part-time job'),
    ('gift', 'Gift'),
    ('other_income', 'Other income'),
]
EXPENSE_CATEGORIES = [
    ('tuition', 'Tuition & fees'),
    ('books', 'Books & supplies'),
    ('food', 'Food'),
    ('rent', 'Rent & housing'),
    ('transport', 'Transport'),
    ('data', 'Airtime & data'),
    ('health', 'Health'),
    ('fun', 'Entertainment'),
    ('other_expense', 'Other expense'),
]
CATEGORY_CHOICES = [('Income', INCOME_CATEGORIES), ('Expense', EXPENSE_CATEGORIES)]
CATEGORY_LABELS = dict(INCOME_CATEGORIES + EXPENSE_CATEGORIES)
CATEGORIES_BY_KIND = {
    INCOME: {key for key, _ in INCOME_CATEGORIES},
    EXPENSE: {key for key, _ in EXPENSE_CATEGORIES},
}

MIN_AMOUNT = Decimal('0.01')
MAX_AMOUNT = Decimal('100000000')  # 100 million: anything larger is almost certainly a typo


class TransactionQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(user=user)

    def total(self, kind):
        return self.filter(kind=kind).aggregate(s=models.Sum('amount'))['s'] or Decimal('0')


class Transaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    kind = models.CharField(max_length=7, choices=KIND_CHOICES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(MIN_AMOUNT), MaxValueValidator(MAX_AMOUNT)],
    )
    description = models.CharField(max_length=140, blank=True)
    date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TransactionQuerySet.as_manager()

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [models.Index(fields=['user', 'date'])]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name='transaction_amount_positive'),
        ]

    def __str__(self):
        return f'{self.get_kind_display()} {self.amount} ({self.category_label})'

    @property
    def category_label(self):
        return CATEGORY_LABELS.get(self.category, self.category)

    @property
    def is_income(self):
        return self.kind == INCOME


class Budget(models.Model):
    """A monthly spending limit for one expense category."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='budgets')
    category = models.CharField(max_length=20, choices=EXPENSE_CATEGORIES)
    monthly_limit = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('1')), MaxValueValidator(MAX_AMOUNT)],
    )

    class Meta:
        ordering = ['category']
        constraints = [
            models.UniqueConstraint(fields=['user', 'category'], name='one_budget_per_category'),
            models.CheckConstraint(condition=models.Q(monthly_limit__gt=0), name='budget_limit_positive'),
        ]

    def __str__(self):
        return f'{self.category_label}: {self.monthly_limit}'

    @property
    def category_label(self):
        return CATEGORY_LABELS.get(self.category, self.category)

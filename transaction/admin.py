from django.contrib import admin

from .models import Budget, Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'user', 'kind', 'category', 'amount', 'description')
    list_filter = ('kind', 'category')
    search_fields = ('description', 'user__username')
    date_hierarchy = 'date'


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'monthly_limit')

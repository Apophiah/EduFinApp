"""Pages for the signed-in user.

Every view here requires login (LoginRequiredMiddleware plus @login_required, so the
rule still holds if the middleware is ever removed), and every query is filtered by
`request.user`: asking for someone else's transaction returns 404, not their data.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from accounts import audit
from accounts.models import AuditEvent

from . import stats
from .forms import BudgetForm, TransactionFilterForm, TransactionForm
from .models import Budget, Transaction


@login_required
def dashboard(request):
    context = {
        'summary': stats.summary(request.user),
        'bars': stats.monthly_bars(request.user),
        'donut': stats.expense_breakdown(request.user),
        'budgets': stats.budget_progress(request.user),
        'recent': Transaction.objects.for_user(request.user)[:5],
    }
    return render(request, 'transaction/dashboard.html', context)


@login_required
def transaction_list(request):
    qs = Transaction.objects.for_user(request.user)
    filters = TransactionFilterForm(request.GET or None)
    if filters.is_valid():
        data = filters.cleaned_data
        if data['q']:
            qs = qs.filter(Q(description__icontains=data['q']))
        if data['kind']:
            qs = qs.filter(kind=data['kind'])
        if data['category']:
            qs = qs.filter(category=data['category'])
        if data['month']:
            year, month = map(int, data['month'].split('-'))
            qs = qs.filter(date__year=year, date__month=month)

    page = Paginator(qs, 15).get_page(request.GET.get('page'))
    query = request.GET.copy()
    query.pop('page', None)
    return render(request, 'transaction/list.html', {
        'page': page,
        'filters': filters,
        'income_total': qs.total('income'),
        'expense_total': qs.total('expense'),
        'querystring': query.urlencode(),
    })


@login_required
@require_http_methods(['GET', 'POST'])
def transaction_create(request):
    initial = {'kind': request.GET.get('kind') if request.GET.get('kind') in ('income', 'expense') else 'expense'}
    form = TransactionForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        tx = form.save(commit=False)
        tx.user = request.user  # never taken from the form
        tx.save()
        audit.record(request, AuditEvent.TX_CREATE, detail=f'id={tx.pk} {tx.kind} {tx.amount}')
        messages.success(request, f'{tx.get_kind_display()} of {tx.amount:,.2f} added.')
        return redirect('transaction_list')
    return render(request, 'transaction/form.html', {'form': form, 'is_edit': False})


@login_required
@require_http_methods(['GET', 'POST'])
def transaction_update(request, pk):
    tx = get_object_or_404(Transaction, pk=pk, user=request.user)
    form = TransactionForm(request.POST or None, instance=tx)
    if request.method == 'POST' and form.is_valid():
        form.save()
        audit.record(request, AuditEvent.TX_UPDATE, detail=f'id={tx.pk} {tx.kind} {tx.amount}')
        messages.success(request, 'Transaction updated.')
        return redirect('transaction_list')
    return render(request, 'transaction/form.html', {'form': form, 'is_edit': True, 'tx': tx})


@login_required
@require_http_methods(['GET', 'POST'])
def transaction_delete(request, pk):
    tx = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        detail = f'id={tx.pk} {tx.kind} {tx.amount}'
        tx.delete()
        audit.record(request, AuditEvent.TX_DELETE, detail=detail)
        messages.success(request, 'Transaction deleted.')
        return redirect('transaction_list')
    return render(request, 'transaction/confirm_delete.html', {'tx': tx})


@login_required
@require_http_methods(['GET', 'POST'])
def budgets(request):
    form = BudgetForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        budget, created = Budget.objects.update_or_create(
            user=request.user, category=form.cleaned_data['category'],
            defaults={'monthly_limit': form.cleaned_data['monthly_limit']},
        )
        audit.record(request, AuditEvent.BUDGET_SAVE, detail=f'{budget.category} {budget.monthly_limit}')
        messages.success(request, f'Budget for {budget.category_label} {"set" if created else "updated"}.')
        return redirect('budgets')
    return render(request, 'transaction/budgets.html', {
        'form': form,
        'budgets': stats.budget_progress(request.user),
        'month_label': stats.summary(request.user)['month_label'],
    })


@login_required
@require_POST
def budget_delete(request, pk):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    audit.record(request, AuditEvent.BUDGET_DELETE, detail=budget.category)
    budget.delete()
    messages.success(request, 'Budget removed.')
    return redirect('budgets')


@login_required
def learn(request):
    return render(request, 'transaction/learn.html')

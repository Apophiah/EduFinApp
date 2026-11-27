import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditEvent

from . import stats
from .forms import TransactionForm
from .models import Budget, Transaction

User = get_user_model()
PASSWORD = 'Str0ng-test-passphrase!'


def make_tx(user, **kwargs):
    data = {'kind': 'expense', 'category': 'food', 'amount': Decimal('1500'), 'description': 'Lunch',
            'date': timezone.localdate()}
    data.update(kwargs)
    return Transaction.objects.create(user=user, **data)


class BaseCase(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user('alice', 'alice@example.com', PASSWORD)
        self.bob = User.objects.create_user('bob', 'bob@example.com', PASSWORD)
        self.client.force_login(self.alice)

    def form_data(self, **overrides):
        data = {'kind': 'expense', 'category': 'food', 'amount': '2500',
                'date': timezone.localdate().isoformat(), 'description': 'Groceries'}
        data.update(overrides)
        return data


class LoginRequiredTests(TestCase):
    """Every private page redirects anonymous visitors to the login page."""

    def test_private_pages_redirect_to_login(self):
        tx_user = User.objects.create_user('carol', password=PASSWORD)
        tx = make_tx(tx_user)
        budget = Budget.objects.create(user=tx_user, category='food', monthly_limit=100)
        urls = [
            reverse('dashboard'), reverse('transaction_list'), reverse('transaction_create'),
            reverse('transaction_update', args=[tx.pk]), reverse('transaction_delete', args=[tx.pk]),
            reverse('budgets'), reverse('learn'),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response['Location'].startswith(reverse('login')))
        response = self.client.post(reverse('budget_delete', args=[budget.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Budget.objects.filter(pk=budget.pk).exists())

    def test_public_pages(self):
        self.assertEqual(self.client.get(reverse('login')).status_code, 200)
        self.assertEqual(self.client.get(reverse('signup')).status_code, 200)
        self.assertEqual(self.client.get(reverse('health')).json(), {'status': 'OK'})

    def test_api_requires_authentication(self):
        self.assertEqual(self.client.get('/api/transactions/').status_code, 403)
        self.assertEqual(self.client.get('/api/summary/').status_code, 403)
        self.assertEqual(self.client.get('/testing').status_code, 403)


class OwnershipTests(BaseCase):
    """Users can only see and change their own transactions and budgets."""

    def setUp(self):
        super().setUp()
        self.mine = make_tx(self.alice, description='alice-lunch')
        self.theirs = make_tx(self.bob, description='bob-secret', amount=Decimal('99999'))

    def test_list_shows_only_own_transactions(self):
        response = self.client.get(reverse('transaction_list'))
        self.assertContains(response, 'alice-lunch')
        self.assertNotContains(response, 'bob-secret')

    def test_dashboard_totals_only_own_transactions(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['summary']['month_expense'], Decimal('1500'))
        self.assertNotContains(response, 'bob-secret')

    def test_cannot_view_edit_or_delete_others_transaction(self):
        edit = reverse('transaction_update', args=[self.theirs.pk])
        delete = reverse('transaction_delete', args=[self.theirs.pk])
        self.assertEqual(self.client.get(edit).status_code, 404)
        self.assertEqual(self.client.post(edit, self.form_data(amount='1')).status_code, 404)
        self.assertEqual(self.client.get(delete).status_code, 404)
        self.assertEqual(self.client.post(delete).status_code, 404)
        self.theirs.refresh_from_db()
        self.assertEqual(self.theirs.amount, Decimal('99999'))

    def test_cannot_delete_others_budget(self):
        budget = Budget.objects.create(user=self.bob, category='food', monthly_limit=100)
        self.assertEqual(self.client.post(reverse('budget_delete', args=[budget.pk])).status_code, 404)
        self.assertTrue(Budget.objects.filter(pk=budget.pk).exists())

    def test_user_field_cannot_be_injected(self):
        self.client.post(reverse('transaction_create'), self.form_data(user=self.bob.pk, description='injected'))
        tx = Transaction.objects.get(description='injected')
        self.assertEqual(tx.user, self.alice)

    def test_api_lists_only_own(self):
        data = self.client.get('/api/transactions/').json()
        self.assertEqual([row['description'] for row in data], ['alice-lunch'])
        self.assertEqual(self.client.get(f'/api/transactions/{self.theirs.pk}/').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/transactions/{self.theirs.pk}/').status_code, 404)
        self.assertTrue(Transaction.objects.filter(pk=self.theirs.pk).exists())

    def test_api_create_sets_owner(self):
        response = self.client.post('/api/transactions/', {
            'kind': 'income', 'category': 'allowance', 'amount': '5000',
            'date': timezone.localdate().isoformat(), 'user': self.bob.pk,
        }, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Transaction.objects.get(pk=response.json()['id']).user, self.alice)


class CrudTests(BaseCase):
    def test_create_edit_delete(self):
        response = self.client.post(reverse('transaction_create'), self.form_data())
        self.assertRedirects(response, reverse('transaction_list'))
        tx = Transaction.objects.get(user=self.alice)
        self.assertEqual(tx.amount, Decimal('2500'))

        self.client.post(reverse('transaction_update', args=[tx.pk]), self.form_data(amount='3000'))
        tx.refresh_from_db()
        self.assertEqual(tx.amount, Decimal('3000'))

        self.assertEqual(self.client.get(reverse('transaction_delete', args=[tx.pk])).status_code, 200)
        self.assertTrue(Transaction.objects.filter(pk=tx.pk).exists(), 'GET must not delete')
        self.client.post(reverse('transaction_delete', args=[tx.pk]))
        self.assertFalse(Transaction.objects.filter(pk=tx.pk).exists())

        actions = list(AuditEvent.objects.filter(user=self.alice).values_list('action', flat=True))
        for action in (AuditEvent.TX_CREATE, AuditEvent.TX_UPDATE, AuditEvent.TX_DELETE):
            self.assertIn(action, actions)

    def test_filters(self):
        make_tx(self.alice, kind='income', category='allowance', description='pocket money')
        make_tx(self.alice, description='bus', category='transport')
        response = self.client.get(reverse('transaction_list'), {'kind': 'income'})
        self.assertContains(response, 'pocket money')
        self.assertNotContains(response, '>bus<')
        response = self.client.get(reverse('transaction_list'), {'q': 'bus'})
        self.assertEqual(response.context['page'].paginator.count, 1)

    def test_bad_filters_are_ignored_safely(self):
        response = self.client.get(reverse('transaction_list'), {'month': "2024-13' OR 1=1", 'kind': 'hack'})
        self.assertEqual(response.status_code, 200)

    def test_budget_upsert_and_progress(self):
        self.client.post(reverse('budgets'), {'category': 'food', 'monthly_limit': '1000'})
        self.client.post(reverse('budgets'), {'category': 'food', 'monthly_limit': '2000'})
        self.assertEqual(Budget.objects.get(user=self.alice, category='food').monthly_limit, Decimal('2000'))
        make_tx(self.alice, amount=Decimal('2500'))
        item = stats.budget_progress(self.alice)[0]
        self.assertEqual(item['state'], 'over')
        self.assertEqual(item['bar'], 100)

    def test_budget_rejects_income_category(self):
        response = self.client.post(reverse('budgets'), {'category': 'allowance', 'monthly_limit': '1000'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Budget.objects.exists())


class ValidationTests(TestCase):
    def form(self, **overrides):
        data = {'kind': 'expense', 'category': 'food', 'amount': '100',
                'date': timezone.localdate().isoformat(), 'description': 'ok'}
        data.update(overrides)
        return TransactionForm(data)

    def test_valid(self):
        self.assertTrue(self.form().is_valid())

    def test_amount_must_be_positive_and_reasonable(self):
        for amount in ('0', '-5', '0.001', '100000001', 'abc', ''):
            with self.subTest(amount=amount):
                self.assertFalse(self.form(amount=amount).is_valid())

    def test_category_must_match_kind(self):
        form = self.form(kind='income', category='food')
        self.assertFalse(form.is_valid())
        self.assertIn('category', form.errors)
        self.assertTrue(self.form(kind='income', category='allowance').is_valid())

    def test_unknown_kind_or_category(self):
        self.assertFalse(self.form(kind='loan').is_valid())
        self.assertFalse(self.form(category='bitcoin').is_valid())

    def test_date_range(self):
        far_future = timezone.localdate() + datetime.timedelta(days=400)
        self.assertFalse(self.form(date=far_future.isoformat()).is_valid())
        self.assertFalse(self.form(date='1999-12-31').is_valid())

    def test_description_is_cleaned(self):
        form = self.form(description='  two   spaces  ')
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['description'], 'two spaces')
        self.assertFalse(self.form(description='bad\x00byte').is_valid())
        self.assertFalse(self.form(description='x' * 141).is_valid())

    def test_html_in_description_is_escaped(self):
        user = User.objects.create_user('eve', password=PASSWORD)
        make_tx(user, description='<script>alert(1)</script>')
        self.client.force_login(user)
        response = self.client.get(reverse('transaction_list'))
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;')

    def test_api_validation(self):
        user = User.objects.create_user('dan', password=PASSWORD)
        self.client.force_login(user)
        response = self.client.post('/api/transactions/', {
            'kind': 'income', 'category': 'food', 'amount': '-3', 'date': '1990-01-01',
        }, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('amount', response.json())
        self.assertIn('date', response.json())
        self.assertFalse(Transaction.objects.exists())


class CsrfTests(BaseCase):
    def test_forms_reject_posts_without_csrf_token(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.alice)
        response = client.post(reverse('transaction_create'), self.form_data())
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Transaction.objects.exists())

    def test_api_rejects_unsafe_methods_without_csrf_token(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.alice)
        response = client.post('/api/transactions/', {'kind': 'income', 'category': 'gift', 'amount': '5',
                                                      'date': timezone.localdate().isoformat()},
                               content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_every_post_form_has_a_token(self):
        tx = make_tx(self.alice)
        Budget.objects.create(user=self.alice, category='food', monthly_limit=100)
        for url in (reverse('transaction_create'), reverse('transaction_update', args=[tx.pk]),
                    reverse('transaction_delete', args=[tx.pk]), reverse('budgets'), reverse('dashboard')):
            with self.subTest(url=url):
                html = self.client.get(url).content.decode()
                self.assertEqual(html.count('method="post"'), html.count('csrfmiddlewaretoken'))


class StatsTests(BaseCase):
    def test_summary_and_charts(self):
        today = timezone.localdate()
        make_tx(self.alice, kind='income', category='allowance', amount=Decimal('10000'))
        make_tx(self.alice, amount=Decimal('2500'))
        make_tx(self.alice, amount=Decimal('500'), category='transport')
        last_year = today.replace(year=today.year - 1)
        make_tx(self.alice, amount=Decimal('700'), date=last_year)

        s = stats.summary(self.alice)
        self.assertEqual(s['month_income'], Decimal('10000'))
        self.assertEqual(s['month_expense'], Decimal('3000'))
        self.assertEqual(s['balance'], Decimal('6300'))
        self.assertEqual(s['savings_rate'], 70)

        bars = stats.monthly_bars(self.alice)
        self.assertEqual(len(bars['months']), 6)
        self.assertEqual(bars['months'][-1]['income_h'], 175)

        donut = stats.expense_breakdown(self.alice)
        self.assertEqual([s['pct'] for s in donut['segments']], [83, 17])

        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'bar-income')
        self.assertContains(response, 'donut-seg')

    def test_add_months(self):
        self.assertEqual(stats.add_months(datetime.date(2025, 11, 1), 3), datetime.date(2026, 2, 1))
        self.assertEqual(stats.add_months(datetime.date(2025, 1, 1), -1), datetime.date(2024, 12, 1))

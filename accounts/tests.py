from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import AuditEvent

User = get_user_model()
PASSWORD = 'Str0ng-test-passphrase!'


class SignUpTests(TestCase):
    def post(self, **overrides):
        data = {'username': 'newstudent', 'first_name': 'Nia', 'email': 'nia@example.com',
                'password1': PASSWORD, 'password2': PASSWORD}
        data.update(overrides)
        return self.client.post(reverse('signup'), data)

    def test_signup_logs_in_and_hashes_password(self):
        response = self.post()
        self.assertRedirects(response, reverse('dashboard'))
        user = User.objects.get(username='newstudent')
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.password.startswith(('pbkdf2_', 'argon2', 'bcrypt', 'scrypt')))
        self.assertEqual(user.role, 'student')
        self.assertTrue(AuditEvent.objects.filter(user=user, action=AuditEvent.SIGNUP).exists())

    def test_weak_passwords_are_rejected(self):
        for password in ('short1', 'password123', '1234567890123', 'newstudent99'):
            with self.subTest(password=password):
                response = self.post(password1=password, password2=password)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(User.objects.filter(username='newstudent').exists())

    def test_duplicate_email_rejected(self):
        User.objects.create_user('someone', 'nia@example.com', PASSWORD)
        response = self.post(email='NIA@example.com')
        self.assertContains(response, 'already exists')

    def test_role_cannot_be_chosen_at_signup(self):
        self.post(role='staff', is_staff='on', is_superuser='on')
        user = User.objects.get(username='newstudent')
        self.assertEqual(user.role, 'student')
        self.assertFalse(user.is_staff or user.is_superuser)


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', 'alice@example.com', PASSWORD)

    def login(self, password):
        return self.client.post(reverse('login'), {'username': 'alice', 'password': password})

    def test_login_and_logout(self):
        self.assertRedirects(self.login(PASSWORD), reverse('dashboard'))
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405, 'logout must be POST-only')
        self.assertRedirects(self.client.post(reverse('logout')), reverse('login'))
        actions = set(AuditEvent.objects.values_list('action', flat=True))
        self.assertTrue({AuditEvent.LOGIN, AuditEvent.LOGOUT} <= actions)

    def test_failed_logins_are_audited_and_throttled(self):
        for _ in range(5):
            self.assertEqual(self.login('wrong-password').status_code, 200)
        self.assertEqual(AuditEvent.objects.filter(action=AuditEvent.LOGIN_FAILED).count(), 5)
        response = self.login(PASSWORD)  # correct password, but locked out
        self.assertContains(response, 'Too many failed attempts')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertTrue(AuditEvent.objects.filter(action=AuditEvent.LOGIN_BLOCKED).exists())

    def test_open_redirect_is_blocked(self):
        response = self.client.post(reverse('login') + '?next=https://evil.example/',
                                    {'username': 'alice', 'password': PASSWORD,
                                     'next': 'https://evil.example/'})
        self.assertRedirects(response, reverse('dashboard'))

    def test_audit_admin_is_read_only(self):
        admin = User.objects.create_superuser('root', 'root@example.com', PASSWORD)
        self.client.force_login(admin)
        AuditEvent.objects.create(action=AuditEvent.LOGIN, username='x')
        event = AuditEvent.objects.first()
        self.assertEqual(self.client.get('/admin/accounts/auditevent/add/').status_code, 403)
        self.client.post(f'/admin/accounts/auditevent/{event.pk}/delete/', {'post': 'yes'})
        self.assertTrue(AuditEvent.objects.filter(pk=event.pk).exists())


class SecuritySettingsTests(TestCase):
    def test_password_validators_configured(self):
        names = [v['NAME'].rsplit('.', 1)[-1] for v in settings.AUTH_PASSWORD_VALIDATORS]
        self.assertEqual(names, ['UserAttributeSimilarityValidator', 'MinimumLengthValidator',
                                 'CommonPasswordValidator', 'NumericPasswordValidator'])

    def test_secret_key_not_the_old_committed_one(self):
        # The key that used to be hard-coded in settings.py started with this prefix.
        self.assertFalse(settings.SECRET_KEY.startswith('django-insecure-'))

    def test_cookies_are_http_only(self):
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertTrue(settings.CSRF_COOKIE_HTTPONLY)

    def test_security_headers(self):
        response = self.client.get(reverse('login'))
        csp = response.headers['Content-Security-Policy']
        self.assertIn("script-src 'self'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertNotIn('unsafe-inline', csp)
        self.assertEqual(response.headers['X-Frame-Options'], 'DENY')
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response.headers['Referrer-Policy'], 'same-origin')

    def test_no_inline_scripts_or_styles_in_pages(self):
        user = User.objects.create_user('alice', password=PASSWORD)
        self.client.force_login(user)
        for name in ('dashboard', 'transaction_list', 'transaction_create', 'budgets', 'learn'):
            with self.subTest(page=name):
                html = self.client.get(reverse(name)).content.decode()
                self.assertNotRegex(html, r'<script(?![^>]*\bsrc=)[^>]*>')
                self.assertNotIn(' style="', html)
                self.assertNotIn('<style', html)

    @override_settings(DEBUG=False)
    def test_debug_off_hides_details(self):
        response = self.client.get('/this-page-does-not-exist/')
        self.assertIn(response.status_code, (302, 404))
        self.assertNotIn(b'Traceback', response.content)

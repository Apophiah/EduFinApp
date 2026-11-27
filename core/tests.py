from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Testing


class CoreApiTests(TestCase):
    def test_health_is_public(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'OK'})

    def test_health_rejects_post(self):
        self.assertEqual(self.client.post('/health').status_code, 405)

    def test_testing_endpoint_returns_items_for_signed_in_users(self):
        Testing.objects.create(name='Sample', description='Demo item')
        user = get_user_model().objects.create_user('alice', password='Str0ng-test-passphrase!')
        self.client.force_login(user)
        response = self.client.get('/testing')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['name'], 'Sample')

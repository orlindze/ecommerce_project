from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AccountsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ivan', 'ivan@example.com', 'pass12345')

    def test_phone_is_optional(self):
        self.assertIn(self.user.phone, (None, ''))

    def test_profile_created_for_new_user(self):
        self.assertTrue(hasattr(self.user, 'profile'))

    def test_login_success(self):
        response = self.client.post(reverse('login'), {'username': 'ivan', 'password': 'pass12345'})
        self.assertRedirects(response, settings.LOGIN_REDIRECT_URL, fetch_redirect_response=False)

    def test_login_wrong_password(self):
        response = self.client.post(reverse('login'), {'username': 'ivan', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_profile_requires_login(self):
        url = reverse('profile')
        self.assertRedirects(self.client.get(url), f'{settings.LOGIN_URL}?next={url}',
                             fetch_redirect_response=False)

    def test_profile_opens_for_logged_in_user(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('profile')).status_code, 200)

    def test_register_page_opens(self):
        self.assertEqual(self.client.get(reverse('register')).status_code, 200)

    def test_logout(self):
        self.client.force_login(self.user)
        self.client.post(reverse('logout'))
        self.assertNotIn('_auth_user_id', self.client.session)
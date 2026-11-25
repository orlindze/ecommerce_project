from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'ecommerce.ratelimit.RateLimitMiddleware',
]
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}


@override_settings(MIDDLEWARE=MIDDLEWARE, CACHES=CACHES,
                   RATELIMIT_RULES={'login': (3, 60)}, RATELIMIT_GLOBAL=(1000, 60))
class RateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse('login')
        self.bad = {'username': 'x', 'password': 'y'}

    def test_login_post_blocked_after_limit(self):
        for _ in range(3):
            self.assertEqual(self.client.post(self.url, self.bad).status_code, 200)
        response = self.client.post(self.url, self.bad)
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)

    def test_get_requests_not_limited_by_rule(self):
        for _ in range(6):
            self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_limit_is_per_ip(self):
        for _ in range(4):
            self.client.post(self.url, self.bad, REMOTE_ADDR='10.0.0.1')
        self.assertEqual(self.client.post(self.url, self.bad, REMOTE_ADDR='10.0.0.2').status_code, 200)

    @override_settings(RATELIMIT_GLOBAL=(2, 60))
    def test_global_limit(self):
        self.client.get(self.url)
        self.client.get(self.url)
        self.assertEqual(self.client.get(self.url).status_code, 429)
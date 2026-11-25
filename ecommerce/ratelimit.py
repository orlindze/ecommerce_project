from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

DEFAULT_RULES = {
    'login': (5, 60),
    'register': (5, 60),
    'orders:coupon_apply': (10, 60),
    'orders:checkout': (10, 60),
}
DEFAULT_GLOBAL = (300, 60)


def client_ip(request):
    if getattr(settings, 'RATELIMIT_TRUST_PROXY', False):
        ip = request.META.get('HTTP_X_REAL_IP')
        if ip:
            return ip.strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def exceeded(key, limit, window):
    cache.add(key, 0, window)
    try:
        count = cache.incr(key)
    except ValueError:  # ключ только что протух
        cache.set(key, 1, window)
        count = 1
    return count > limit


def too_many(window):
    response = HttpResponse('Забагато запитів. Спробуйте пізніше.', status=429,
                            content_type='text/plain; charset=utf-8')
    response['Retry-After'] = str(window)
    return response


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        limit, window = getattr(settings, 'RATELIMIT_GLOBAL', DEFAULT_GLOBAL)
        if exceeded(f'rl:global:{client_ip(request)}', limit, window):
            return too_many(window)
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method != 'POST' or request.resolver_match is None:
            return None
        rules = getattr(settings, 'RATELIMIT_RULES', DEFAULT_RULES)
        rule = rules.get(request.resolver_match.view_name)
        if rule and exceeded(f'rl:{request.resolver_match.view_name}:{client_ip(request)}', *rule):
            return too_many(rule[1])
        return None
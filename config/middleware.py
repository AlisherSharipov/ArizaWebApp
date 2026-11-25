from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse


class AdminLoginRateLimitMiddleware:
    """Rate-limits repeated failed POST attempts to the Django Admin login page."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_admin_login_post = (
            request.method == "POST" and request.path.rstrip("/") == "/admin/login"
        )
        if not is_admin_login_post:
            return self.get_response(request)

        max_attempts = getattr(settings, "ADMIN_LOGIN_MAX_ATTEMPTS", 5)
        lockout_seconds = getattr(settings, "ADMIN_LOGIN_LOCKOUT_SECONDS", 300)
        client_ip = self._get_client_ip(request)
        cache_key = f"admin_login_attempts:{client_ip}"

        attempts = cache.get(cache_key, 0)
        if attempts >= max_attempts:
            return HttpResponse(
                "Juda ko'p muvaffaqiyatsiz kirish urinishlari. Iltimos, birozdan so'ng qayta urinib ko'ring.",
                status=429,
                content_type="text/plain; charset=utf-8",
            )

        response = self.get_response(request)

        # Successful Django admin login redirects (302) and authenticates the staff user
        if response.status_code == 302 and request.user.is_authenticated:
            cache.delete(cache_key)
        elif response.status_code == 200:
            cache.set(cache_key, attempts + 1, timeout=lockout_seconds)

        return response

    @staticmethod
    def _get_client_ip(request) -> str:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")

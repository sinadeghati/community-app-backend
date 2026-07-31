from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie


@method_decorator(ensure_csrf_cookie, name="dispatch")
class AdminCsrfView(View):
    """Issue CSRF cookie for Korook admin SPA (Django view, not DRF)."""

    def get(self, request):
        return JsonResponse({"csrfToken": get_token(request)})

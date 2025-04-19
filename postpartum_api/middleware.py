from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

class CSRFExemptMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path in settings.CSRF_EXEMPT_URLS:
            setattr(request, '_dont_enforce_csrf_checks', True) 
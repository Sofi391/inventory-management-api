import logging
import time

logger = logging.getLogger('request')


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        user = request.user if hasattr(request, 'user') else 'anonymous'
        response = self.get_response(request)
        elapsed = time.time() - start

        level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(
            level,
            "%s %s | user=%s | status=%s | elapsed=%.3fs",
            request.method,
            request.path,
            user,
            response.status_code,
            elapsed,
        )
        return response

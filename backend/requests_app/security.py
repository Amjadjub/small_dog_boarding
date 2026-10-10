import hashlib
from functools import wraps

from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response


def rate_limit(scope, limit, period_seconds):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            # REMOTE_ADDR cannot be spoofed by a client-supplied forwarding header.
            # A production reverse proxy should overwrite it with the trusted client address.
            address = request.META.get("REMOTE_ADDR", "unknown")
            identity = request.data.get("email") or request.data.get("username") or ""
            digest = hashlib.sha256(f"{address}:{str(identity).lower()}".encode()).hexdigest()
            key = f"rate:{scope}:{digest}"
            if cache.add(key, 1, timeout=period_seconds):
                count = 1
            else:
                try:
                    count = cache.incr(key)
                except ValueError:
                    cache.set(key, 1, timeout=period_seconds)
                    count = 1
            if count > limit:
                return Response({"detail": "יותר מדי ניסיונות. נסו שוב מאוחר יותר."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator

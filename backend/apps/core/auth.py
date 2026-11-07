# WRITTEN, NOT RUN
import hashlib

from rest_framework import authentication, exceptions

from .models import ApiSession


class BearerTokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        h = request.headers.get("Authorization", "")
        if not h.startswith("Bearer "):
            return None
        digest = hashlib.sha256(h[7:].encode()).hexdigest()
        s = ApiSession.objects.select_related("user").filter(token_hash=digest, revoked=False).first()
        if not s:
            raise exceptions.AuthenticationFailed()
        return (s.user, None)

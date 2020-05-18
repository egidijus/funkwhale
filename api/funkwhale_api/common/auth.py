from urllib.parse import parse_qs

from django.contrib.auth.models import AnonymousUser
from rest_framework import exceptions
from rest_framework_jwt.authentication import BaseJSONWebTokenAuthentication

from funkwhale_api.users.models import User


class TokenHeaderAuth(BaseJSONWebTokenAuthentication):
    def get_jwt_value(self, request):

        try:
            qs = request.get("query_string", b"").decode("utf-8")
            parsed = parse_qs(qs)
            token = parsed["token"][0]
        except KeyError:
            raise exceptions.AuthenticationFailed("No token")

        if not token:
            raise exceptions.AuthenticationFailed("Empty token")

        return token


class TokenAuthMiddleware:
    def __init__(self, inner):
        # Store the ASGI application we were passed
        self.inner = inner

    def __call__(self, scope):
        if "user" in scope:
            # auth already handled
            return self.inner(scope)
        # XXX: 1.0 remove this, replace with websocket/scopedtoken
        auth = TokenHeaderAuth()
        try:
            user, token = auth.authenticate(scope)
        except (User.DoesNotExist, exceptions.AuthenticationFailed):
            user = AnonymousUser()

        scope["user"] = user
        return self.inner(scope)

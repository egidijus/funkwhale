from django.conf import settings
from django.core import signing

from rest_framework import authentication
from rest_framework import exceptions
from django.core.exceptions import ValidationError

from .oauth import scopes as available_scopes

from . import models


def generate_scoped_token(user_id, user_secret, scopes):
    if set(scopes) & set(available_scopes.SCOPES_BY_ID) != set(scopes):
        raise ValueError("{} contains invalid scopes".format(scopes))

    return signing.dumps(
        {
            "user_id": user_id,
            "user_secret": str(user_secret),
            "scopes": list(sorted(scopes)),
        },
        salt="scoped_tokens",
    )


def authenticate_scoped_token(token):
    try:
        payload = signing.loads(
            token, salt="scoped_tokens", max_age=settings.SCOPED_TOKENS_MAX_AGE,
        )
    except signing.BadSignature:
        raise exceptions.AuthenticationFailed("Invalid token signature")

    try:
        user_id = int(payload["user_id"])
        user_secret = str(payload["user_secret"])
        scopes = list(payload["scopes"])
    except (KeyError, ValueError, TypeError):
        raise exceptions.AuthenticationFailed("Invalid scoped token payload")

    try:
        user = (
            models.User.objects.all()
            .for_auth()
            .get(pk=user_id, secret_key=user_secret, is_active=True)
        )
    except (models.User.DoesNotExist, ValidationError):
        raise exceptions.AuthenticationFailed("Invalid user")

    return user, scopes


class ScopedTokenAuthentication(authentication.BaseAuthentication):
    """
    Used when signed token returned by generate_scoped_token are provided via
    token= in GET requests. Mostly for <audio src=""> urls, since it's not possible
    to override headers sent by the browser when loading media.
    """

    def authenticate(self, request):
        data = request.GET
        token = data.get("token")
        if not token:
            return None

        try:
            user, scopes = authenticate_scoped_token(token)
        except exceptions.AuthenticationFailed:
            raise exceptions.AuthenticationFailed("Invalid token")

        setattr(request, "scopes", scopes)
        setattr(request, "actor", user.actor)
        return user, None

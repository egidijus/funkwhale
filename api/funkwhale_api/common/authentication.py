from django.conf import settings
from django.utils.encoding import smart_text
from django.utils.translation import ugettext as _

from django.core.cache import cache

from allauth.account.utils import send_email_confirmation
from oauth2_provider.contrib.rest_framework.authentication import (
    OAuth2Authentication as BaseOAuth2Authentication,
)
from rest_framework import exceptions
from rest_framework_jwt import authentication
from rest_framework_jwt.settings import api_settings

from funkwhale_api.users import models as users_models


def should_verify_email(user):
    if user.is_superuser:
        return False
    has_unverified_email = not user.has_verified_primary_email
    mandatory_verification = settings.ACCOUNT_EMAIL_VERIFICATION != "optional"
    return has_unverified_email and mandatory_verification


class UnverifiedEmail(Exception):
    def __init__(self, user):
        self.user = user


def resend_confirmation_email(request, user):
    THROTTLE_DELAY = 500
    cache_key = "auth:resent-email-confirmation:{}".format(user.pk)
    if cache.get(cache_key):
        return False

    done = send_email_confirmation(request, user)
    cache.set(cache_key, True, THROTTLE_DELAY)
    return done


class OAuth2Authentication(BaseOAuth2Authentication):
    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except UnverifiedEmail as e:
            request.oauth2_error = {"error": "unverified_email"}
            resend_confirmation_email(request, e.user)


class ApplicationTokenAuthentication(object):
    def authenticate(self, request):
        try:
            header = request.headers["Authorization"]
        except KeyError:
            return

        if "Bearer" not in header:
            return

        token = header.split()[-1].strip()

        try:
            application = users_models.Application.objects.exclude(user=None).get(
                token=token
            )
        except users_models.Application.DoesNotExist:
            return
        user = users_models.User.objects.all().for_auth().get(id=application.user_id)
        if not user.is_active:
            msg = _("User account is disabled.")
            raise exceptions.AuthenticationFailed(msg)

        if should_verify_email(user):
            raise UnverifiedEmail(user)

        request.scopes = application.scope.split()
        return user, None


class BaseJsonWebTokenAuth(object):
    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except UnverifiedEmail as e:
            msg = _("You need to verify your email address.")
            resend_confirmation_email(request, e.user)
            raise exceptions.AuthenticationFailed(msg)

    def authenticate_credentials(self, payload):
        """
        We have to implement this method by hand to ensure we can check that the
        User has a verified email, if required
        """
        User = authentication.get_user_model()
        username = authentication.jwt_get_username_from_payload(payload)

        if not username:
            msg = _("Invalid payload.")
            raise exceptions.AuthenticationFailed(msg)

        try:
            user = User.objects.get_by_natural_key(username)
        except User.DoesNotExist:
            msg = _("Invalid signature.")
            raise exceptions.AuthenticationFailed(msg)

        if not user.is_active:
            msg = _("User account is disabled.")
            raise exceptions.AuthenticationFailed(msg)

        if should_verify_email(user):
            raise UnverifiedEmail(user)

        return user


class JSONWebTokenAuthenticationQS(
    BaseJsonWebTokenAuth, authentication.BaseJSONWebTokenAuthentication
):

    www_authenticate_realm = "api"

    def get_jwt_value(self, request):
        token = request.query_params.get("jwt")
        if "jwt" in request.query_params and not token:
            msg = _("Invalid Authorization header. No credentials provided.")
            raise exceptions.AuthenticationFailed(msg)
        return token

    def authenticate_header(self, request):
        return '{0} realm="{1}"'.format(
            api_settings.JWT_AUTH_HEADER_PREFIX, self.www_authenticate_realm
        )


class BearerTokenHeaderAuth(
    BaseJsonWebTokenAuth, authentication.BaseJSONWebTokenAuthentication
):
    """
    For backward compatibility purpose, we used Authorization: JWT <token>
    but Authorization: Bearer <token> is probably better.
    """

    www_authenticate_realm = "api"

    def get_jwt_value(self, request):
        auth = authentication.get_authorization_header(request).split()
        auth_header_prefix = "bearer"

        if not auth:
            if api_settings.JWT_AUTH_COOKIE:
                return request.COOKIES.get(api_settings.JWT_AUTH_COOKIE)
            return None

        if smart_text(auth[0].lower()) != auth_header_prefix:
            return None

        if len(auth) == 1:
            msg = _("Invalid Authorization header. No credentials provided.")
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _(
                "Invalid Authorization header. Credentials string "
                "should not contain spaces."
            )
            raise exceptions.AuthenticationFailed(msg)

        return auth[1]

    def authenticate_header(self, request):
        return '{0} realm="{1}"'.format("Bearer", self.www_authenticate_realm)

    def authenticate(self, request):
        auth = super().authenticate(request)
        if auth:
            if not auth[0].actor:
                auth[0].create_actor()
        return auth


class JSONWebTokenAuthentication(
    BaseJsonWebTokenAuth, authentication.JSONWebTokenAuthentication
):
    def authenticate(self, request):
        auth = super().authenticate(request)

        if auth:
            if not auth[0].actor:
                auth[0].create_actor()
        return auth

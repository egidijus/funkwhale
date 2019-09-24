from django.utils.encoding import smart_text
from django.utils.translation import ugettext as _
from oauth2_provider.contrib.rest_framework import (
    OAuth2Authentication as BaseOAuth2Authentication,
)
from rest_framework import exceptions
from rest_framework_jwt import authentication
from rest_framework_jwt.settings import api_settings
from rest_framework.authentication import BasicAuthentication as BaseBasicAuthentication
from rest_framework.authentication import (
    SessionAuthentication as BaseSessionAuthentication,
)


from funkwhale_api.plugins import authentication as plugin_authentication


class JSONWebTokenAuthenticationQS(
    plugin_authentication.AttachPluginsConfMixin,
    authentication.BaseJSONWebTokenAuthentication,
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
    plugin_authentication.AttachPluginsConfMixin,
    authentication.BaseJSONWebTokenAuthentication,
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
    plugin_authentication.AttachPluginsConfMixin,
    authentication.JSONWebTokenAuthentication,
):
    def authenticate(self, request):
        auth = super().authenticate(request)

        if auth:
            if not auth[0].actor:
                auth[0].create_actor()
        return auth


class OAuth2Authentication(
    plugin_authentication.AttachPluginsConfMixin, BaseOAuth2Authentication
):
    pass


class BasicAuthentication(
    plugin_authentication.AttachPluginsConfMixin, BaseBasicAuthentication
):
    pass


class SessionAuthentication(
    plugin_authentication.AttachPluginsConfMixin, BaseSessionAuthentication
):
    pass

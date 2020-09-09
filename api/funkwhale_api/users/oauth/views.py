import json
import urllib.parse

from django import http
from django.utils import timezone
from django.db.models import Q
from rest_framework import mixins, permissions, response, views, viewsets
from rest_framework.decorators import action

from oauth2_provider import exceptions as oauth2_exceptions
from oauth2_provider import views as oauth_views
from oauth2_provider.settings import oauth2_settings

from funkwhale_api.common import throttling

from .. import models
from .permissions import ScopePermission
from . import serializers


class ApplicationViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    anonymous_policy = True
    required_scope = {
        "retrieve": None,
        "create": None,
        "destroy": "write:security",
        "update": "write:security",
        "partial_update": "write:security",
        "refresh_token": "write:security",
        "list": "read:security",
    }
    lookup_field = "client_id"
    queryset = models.Application.objects.all().order_by("-created")
    serializer_class = serializers.ApplicationSerializer
    throttling_scopes = {
        "create": {
            "anonymous": "anonymous-oauth-app",
            "authenticated": "authenticated-oauth-app",
        }
    }

    def get_serializer_class(self):
        if self.request.method.lower() == "post":
            return serializers.CreateApplicationSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        return serializer.save(
            client_type=models.Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=models.Application.GRANT_AUTHORIZATION_CODE,
            user=self.request.user if self.request.user.is_authenticated else None,
            token=models.get_token() if self.request.user.is_authenticated else None,
        )

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        try:
            owned = args[0].user == self.request.user
        except (IndexError, AttributeError):
            owned = False
        if owned:
            serializer_class = serializers.CreateApplicationSerializer

        kwargs["context"] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action in [
            "list",
            "destroy",
            "update",
            "partial_update",
            "refresh_token",
        ]:
            qs = qs.filter(user=self.request.user)
        return qs

    @action(
        detail=True,
        methods=["post"],
        url_name="refresh_token",
        url_path="refresh-token",
    )
    def refresh_token(self, request, *args, **kwargs):
        app = self.get_object()
        if not app.user_id or request.user != app.user:
            return response.Response(status=404)
        app.token = models.get_token()
        app.save(update_fields=["token"])
        serializer = serializers.CreateApplicationSerializer(app)
        return response.Response(serializer.data, status=200)


class GrantViewSet(
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    This is a viewset that list applications that have access to the request user
    account, to allow revoking tokens easily.
    """

    permission_classes = [permissions.IsAuthenticated, ScopePermission]
    required_scope = "security"
    lookup_field = "client_id"
    queryset = models.Application.objects.all().order_by("-created")
    serializer_class = serializers.ApplicationSerializer
    pagination_class = None

    def get_queryset(self):
        now = timezone.now()
        queryset = super().get_queryset()
        grants = models.Grant.objects.filter(user=self.request.user, expires__gt=now)
        access_tokens = models.AccessToken.objects.filter(user=self.request.user)
        refresh_tokens = models.RefreshToken.objects.filter(
            user=self.request.user, revoked=None
        )

        return queryset.filter(
            Q(pk__in=access_tokens.values("application"))
            | Q(pk__in=refresh_tokens.values("application"))
            | Q(pk__in=grants.values("application"))
        ).distinct()

    def perform_create(self, serializer):
        return serializer.save(
            client_type=models.Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=models.Application.GRANT_AUTHORIZATION_CODE,
        )

    def perform_destroy(self, instance):
        application = instance

        access_tokens = application.accesstoken_set.filter(user=self.request.user)
        for token in access_tokens:
            token.revoke()

        refresh_tokens = application.refreshtoken_set.filter(user=self.request.user)
        for token in refresh_tokens:
            try:
                token.revoke()
            except models.AccessToken.DoesNotExist:
                token.access_token = None
                token.revoked = timezone.now()
                token.save(update_fields=["access_token", "revoked"])
        grants = application.grant_set.filter(user=self.request.user)
        grants.delete()


class AuthorizeView(views.APIView, oauth_views.AuthorizationView):
    permission_classes = [permissions.IsAuthenticated]
    server_class = oauth2_settings.OAUTH2_SERVER_CLASS
    validator_class = oauth2_settings.OAUTH2_VALIDATOR_CLASS
    oauthlib_backend_class = oauth2_settings.OAUTH2_BACKEND_CLASS
    skip_authorization_completely = False
    oauth2_data = {}

    def form_invalid(self, form):
        """
        Return a JSON response instead of a template one
        """
        errors = form.errors

        return self.json_payload(errors, status_code=400)

    def post(self, request, *args, **kwargs):
        throttling.check_request(request, "oauth-authorize")
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            return super().form_valid(form)

        except models.Application.DoesNotExist:
            return self.json_payload({"non_field_errors": ["Invalid application"]}, 400)

    def redirect(self, redirect_to, application, token=None):
        if self.request.is_ajax():
            # Web client need this to be able to redirect the user
            query = urllib.parse.urlparse(redirect_to).query
            code = urllib.parse.parse_qs(query)["code"][0]
            return self.json_payload(
                {"redirect_uri": redirect_to, "code": code}, status_code=200
            )

        return super().redirect(redirect_to, application, token)

    def error_response(self, error, application):
        if isinstance(error, oauth2_exceptions.FatalClientError):
            return self.json_payload({"detail": error.oauthlib_error.description}, 400)
        return super().error_response(error, application)

    def json_payload(self, payload, status_code):
        return http.HttpResponse(
            json.dumps(payload), status=status_code, content_type="application/json"
        )

    def handle_no_permission(self):
        return self.json_payload(
            {"detail": "Authentication credentials were not provided."}, 401
        )


class TokenView(oauth_views.TokenView):
    def post(self, request, *args, **kwargs):
        throttling.check_request(request, "oauth-token")
        return super().post(request, *args, **kwargs)


class RevokeTokenView(oauth_views.RevokeTokenView):
    def post(self, request, *args, **kwargs):
        throttling.check_request(request, "oauth-revoke-token")
        return super().post(request, *args, **kwargs)

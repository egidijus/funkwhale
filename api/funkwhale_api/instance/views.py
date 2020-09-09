import json
import logging

from django.conf import settings

from dynamic_preferences.api import serializers
from dynamic_preferences.api import viewsets as preferences_viewsets
from dynamic_preferences.registries import global_preferences_registry
from rest_framework import views
from rest_framework.response import Response

from funkwhale_api.common import middleware
from funkwhale_api.common import preferences
from funkwhale_api.federation import utils as federation_utils
from funkwhale_api.users.oauth import permissions as oauth_permissions

from . import nodeinfo

NODEINFO_2_CONTENT_TYPE = "application/json; profile=http://nodeinfo.diaspora.software/ns/schema/2.0#; charset=utf-8"  # noqa


logger = logging.getLogger(__name__)


class AdminSettings(preferences_viewsets.GlobalPreferencesViewSet):
    pagination_class = None
    permission_classes = [oauth_permissions.ScopePermission]
    required_scope = "instance:settings"


class InstanceSettings(views.APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        manager = global_preferences_registry.manager()
        manager.all()
        all_preferences = manager.model.objects.all().order_by("section", "name")
        api_preferences = [
            p for p in all_preferences if getattr(p.preference, "show_in_api", False)
        ]
        data = serializers.GlobalPreferenceSerializer(api_preferences, many=True).data
        return Response(data, status=200)


class NodeInfo(views.APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        try:
            data = nodeinfo.get()
        except ValueError:
            logger.warn("nodeinfo returned invalid json")
            data = {}
        return Response(data, status=200, content_type=NODEINFO_2_CONTENT_TYPE)


class SpaManifest(views.APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        existing_manifest = middleware.get_spa_file(
            settings.FUNKWHALE_SPA_HTML_ROOT, "manifest.json"
        )
        parsed_manifest = json.loads(existing_manifest)
        parsed_manifest["short_name"] = settings.APP_NAME
        parsed_manifest["start_url"] = federation_utils.full_url("/")
        instance_name = preferences.get("instance__name")
        if instance_name:
            parsed_manifest["short_name"] = instance_name
            parsed_manifest["name"] = instance_name
        instance_description = preferences.get("instance__short_description")
        if instance_description:
            parsed_manifest["description"] = instance_description
        return Response(parsed_manifest, status=200)

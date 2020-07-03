from rest_framework import mixins, viewsets

from django.db.models import Prefetch

from config import plugins

from funkwhale_api.activity import record
from funkwhale_api.common import fields, permissions
from funkwhale_api.music.models import Track
from funkwhale_api.music import utils as music_utils
from . import filters, models, serializers

from funkwhale_api.users.oauth import permissions as oauth_permissions


class ListeningViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):

    serializer_class = serializers.ListeningSerializer
    queryset = models.Listening.objects.all().select_related(
        "user__actor__attachment_icon"
    )

    permission_classes = [
        oauth_permissions.ScopePermission,
        permissions.OwnerPermission,
    ]
    required_scope = "listenings"
    anonymous_policy = "setting"
    owner_checks = ["write"]
    filterset_class = filters.ListeningFilter

    def get_serializer_class(self):
        if self.request.method.lower() in ["head", "get", "options"]:
            return serializers.ListeningSerializer
        return serializers.ListeningWriteSerializer

    def perform_create(self, serializer):
        r = super().perform_create(serializer)
        plugins.trigger_hook(
            plugins.LISTENING_CREATED,
            listening=serializer.instance,
            confs=plugins.get_confs(self.request.user),
        )
        record.send(serializer.instance)
        return r

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(
            fields.privacy_level_query(self.request.user, "user__privacy_level")
        )
        tracks = Track.objects.with_playable_uploads(
            music_utils.get_actor_from_request(self.request)
        ).select_related("artist", "album__artist", "attributed_to")
        return queryset.prefetch_related(Prefetch("track", queryset=tracks))

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["user"] = self.request.user
        return context

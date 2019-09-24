from rest_framework import mixins, viewsets, response
from rest_framework.decorators import action

from django.db.models import Prefetch

from funkwhale_api import plugins
from funkwhale_api.activity import record
from funkwhale_api.common import fields, permissions, utils
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
    queryset = models.Listening.objects.all().select_related("user__actor")

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

    @action(methods=["post"], detail=False)
    def now(self, request, *args, **kwargs):
        serializer = serializers.NowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        utils.on_commit(
            plugins.hooks.dispatch,
            "history.listening.now",
            user=request.user,
            track=serializer.validated_data["track"],
            plugins_conf=request.plugins_conf,
        )
        return response.Response({}, status=204)

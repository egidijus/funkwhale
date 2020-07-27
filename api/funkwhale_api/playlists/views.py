from django.db import transaction
from django.db.models import Count
from rest_framework import exceptions, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from funkwhale_api.common import fields, permissions
from funkwhale_api.music import utils as music_utils
from funkwhale_api.users.oauth import permissions as oauth_permissions

from . import filters, models, serializers


class PlaylistViewSet(
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):

    serializer_class = serializers.PlaylistSerializer
    queryset = (
        models.Playlist.objects.all()
        .select_related("user__actor__attachment_icon")
        .annotate(tracks_count=Count("playlist_tracks", distinct=True))
        .with_covers()
        .with_duration()
    )
    permission_classes = [
        oauth_permissions.ScopePermission,
        permissions.OwnerPermission,
    ]
    required_scope = "playlists"
    anonymous_policy = "setting"
    owner_checks = ["write"]
    filterset_class = filters.PlaylistFilter
    ordering_fields = ("id", "name", "creation_date", "modification_date")

    @action(methods=["get"], detail=True)
    def tracks(self, request, *args, **kwargs):
        playlist = self.get_object()
        plts = playlist.playlist_tracks.all().for_nested_serialization(
            music_utils.get_actor_from_request(request)
        )
        serializer = serializers.PlaylistTrackSerializer(plts, many=True)
        data = {"count": len(plts), "results": serializer.data}
        return Response(data, status=200)

    @action(methods=["post"], detail=True)
    @transaction.atomic
    def add(self, request, *args, **kwargs):
        playlist = self.get_object()
        serializer = serializers.PlaylistAddManySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            plts = playlist.insert_many(
                serializer.validated_data["tracks"],
                serializer.validated_data["allow_duplicates"],
            )
        except exceptions.ValidationError as e:
            payload = {"playlist": e.detail}
            return Response(payload, status=400)
        ids = [p.id for p in plts]
        plts = (
            models.PlaylistTrack.objects.filter(pk__in=ids)
            .order_by("index")
            .for_nested_serialization(music_utils.get_actor_from_request(request))
        )
        serializer = serializers.PlaylistTrackSerializer(plts, many=True)
        data = {"count": len(plts), "results": serializer.data}
        return Response(data, status=201)

    @action(methods=["delete"], detail=True)
    @transaction.atomic
    def clear(self, request, *args, **kwargs):
        playlist = self.get_object()
        playlist.playlist_tracks.all().delete()
        playlist.save(update_fields=["modification_date"])
        return Response(status=204)

    def get_queryset(self):
        return self.queryset.filter(
            fields.privacy_level_query(self.request.user)
        ).with_playable_plts(music_utils.get_actor_from_request(self.request))

    def perform_create(self, serializer):
        return serializer.save(
            user=self.request.user,
            privacy_level=serializer.validated_data.get(
                "privacy_level", self.request.user.privacy_level
            ),
        )

    @action(methods=["post", "delete"], detail=True)
    @transaction.atomic
    def remove(self, request, *args, **kwargs):
        playlist = self.get_object()
        try:
            index = int(request.data["index"])
            assert index >= 0
        except (KeyError, ValueError, AssertionError, TypeError):
            return Response(status=400)

        try:
            plt = playlist.playlist_tracks.by_index(index)
        except models.PlaylistTrack.DoesNotExist:
            return Response(status=404)
        plt.delete(update_indexes=True)

        return Response(status=204)

    @action(methods=["post"], detail=True)
    @transaction.atomic
    def move(self, request, *args, **kwargs):
        playlist = self.get_object()
        try:
            from_index = int(request.data["from"])
            assert from_index >= 0
        except (KeyError, ValueError, AssertionError, TypeError):
            return Response({"detail": "invalid from index"}, status=400)

        try:
            to_index = int(request.data["to"])
            assert to_index >= 0
        except (KeyError, ValueError, AssertionError, TypeError):
            return Response({"detail": "invalid to index"}, status=400)

        try:
            plt = playlist.playlist_tracks.by_index(from_index)
        except models.PlaylistTrack.DoesNotExist:
            return Response(status=404)
        playlist.insert(plt, to_index)
        return Response(status=204)

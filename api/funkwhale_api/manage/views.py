from rest_framework import mixins, response, viewsets
from rest_framework import decorators as rest_decorators

from django.db import transaction
from django.db.models import Count, Prefetch, Q, Sum, OuterRef, Subquery
from django.db.models.functions import Coalesce, Length
from django.shortcuts import get_object_or_404

from funkwhale_api.audio import models as audio_models
from funkwhale_api.common.mixins import MultipleLookupDetailMixin
from funkwhale_api.common import models as common_models
from funkwhale_api.common import preferences, decorators
from funkwhale_api.common import utils as common_utils
from funkwhale_api.favorites import models as favorites_models
from funkwhale_api.federation import models as federation_models
from funkwhale_api.federation import tasks as federation_tasks
from funkwhale_api.federation import utils as federation_utils
from funkwhale_api.history import models as history_models
from funkwhale_api.music import models as music_models
from funkwhale_api.music import views as music_views
from funkwhale_api.moderation import models as moderation_models
from funkwhale_api.moderation import tasks as moderation_tasks
from funkwhale_api.playlists import models as playlists_models
from funkwhale_api.tags import models as tags_models
from funkwhale_api.users import models as users_models


from . import filters, serializers


def get_stats(tracks, target, ignore_fields=[]):
    tracks = list(tracks.values_list("pk", flat=True))
    uploads = music_models.Upload.objects.filter(track__in=tracks)
    fields = {
        "listenings": history_models.Listening.objects.filter(track__in=tracks),
        "mutations": common_models.Mutation.objects.get_for_target(target),
        "playlists": (
            playlists_models.PlaylistTrack.objects.filter(track__in=tracks)
            .values_list("playlist", flat=True)
            .distinct()
        ),
        "track_favorites": (
            favorites_models.TrackFavorite.objects.filter(track__in=tracks)
        ),
        "libraries": (
            uploads.filter(library__channel=None)
            .values_list("library", flat=True)
            .distinct()
        ),
        "channels": (
            uploads.exclude(library__channel=None)
            .values_list("library", flat=True)
            .distinct()
        ),
        "uploads": uploads,
        "reports": moderation_models.Report.objects.get_for_target(target),
    }
    data = {}
    for key, qs in fields.items():
        if key in ignore_fields:
            continue
        data[key] = qs.count()

    data.update(get_media_stats(uploads))
    return data


def get_media_stats(uploads):
    data = {}
    data["media_total_size"] = uploads.aggregate(v=Sum("size"))["v"] or 0
    data["media_downloaded_size"] = (
        uploads.with_file().aggregate(v=Sum("size"))["v"] or 0
    )
    return data


class ManageArtistViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = (
        music_models.Artist.objects.all()
        .order_by("-id")
        .select_related("attributed_to", "attachment_cover", "channel")
        .annotate(_tracks_count=Count("tracks", distinct=True))
        .annotate(_albums_count=Count("albums", distinct=True))
        .prefetch_related(music_views.TAG_PREFETCH)
    )
    serializer_class = serializers.ManageArtistSerializer
    filterset_class = filters.ManageArtistFilterSet
    required_scope = "instance:libraries"
    ordering_fields = ["creation_date", "name"]

    @rest_decorators.action(methods=["get"], detail=True)
    def stats(self, request, *args, **kwargs):
        artist = self.get_object()
        tracks = music_models.Track.objects.filter(
            Q(artist=artist) | Q(album__artist=artist)
        )
        data = get_stats(tracks, artist)
        return response.Response(data, status=200)

    @rest_decorators.action(methods=["post"], detail=False)
    def action(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = serializers.ManageArtistActionSerializer(
            request.data, queryset=queryset
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return response.Response(result, status=200)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["description"] = self.action in ["retrieve", "create", "update"]
        return context


class ManageAlbumViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = (
        music_models.Album.objects.all()
        .order_by("-id")
        .select_related("attributed_to", "artist", "attachment_cover")
        .with_tracks_count()
    )
    serializer_class = serializers.ManageAlbumSerializer
    filterset_class = filters.ManageAlbumFilterSet
    required_scope = "instance:libraries"
    ordering_fields = ["creation_date", "title", "release_date"]

    @rest_decorators.action(methods=["get"], detail=True)
    def stats(self, request, *args, **kwargs):
        album = self.get_object()
        data = get_stats(album.tracks.all(), album)
        return response.Response(data, status=200)

    @rest_decorators.action(methods=["post"], detail=False)
    def action(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = serializers.ManageAlbumActionSerializer(
            request.data, queryset=queryset
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return response.Response(result, status=200)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["description"] = self.action in ["retrieve", "create", "update"]
        return context


uploads_subquery = (
    music_models.Upload.objects.filter(track_id=OuterRef("pk"))
    .order_by()
    .values("track_id")
    .annotate(track_count=Count("track_id"))
    .values("track_count")
)


class ManageTrackViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = (
        music_models.Track.objects.all()
        .order_by("-id")
        .select_related(
            "attributed_to",
            "artist",
            "album__artist",
            "album__attachment_cover",
            "attachment_cover",
        )
        .annotate(uploads_count=Coalesce(Subquery(uploads_subquery), 0))
        .prefetch_related(music_views.TAG_PREFETCH)
    )
    serializer_class = serializers.ManageTrackSerializer
    filterset_class = filters.ManageTrackFilterSet
    required_scope = "instance:libraries"
    ordering_fields = [
        "creation_date",
        "title",
        "album__release_date",
        "position",
        "disc_number",
    ]

    @rest_decorators.action(methods=["get"], detail=True)
    def stats(self, request, *args, **kwargs):
        track = self.get_object()
        data = get_stats(track.__class__.objects.filter(pk=track.pk), track)
        return response.Response(data, status=200)

    @rest_decorators.action(methods=["post"], detail=False)
    def action(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = serializers.ManageTrackActionSerializer(
            request.data, queryset=queryset
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return response.Response(result, status=200)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["description"] = self.action in ["retrieve", "create", "update"]
        return context


uploads_subquery = (
    music_models.Upload.objects.filter(library_id=OuterRef("pk"))
    .order_by()
    .values("library_id")
    .annotate(library_count=Count("library_id"))
    .values("library_count")
)

follows_subquery = (
    federation_models.LibraryFollow.objects.filter(target_id=OuterRef("pk"))
    .order_by()
    .values("target_id")
    .annotate(library_count=Count("target_id"))
    .values("library_count")
)


class ManageLibraryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "uuid"
    queryset = (
        music_models.Library.objects.all()
        .filter(channel=None)
        .order_by("-id")
        .select_related("actor")
        .annotate(
            followers_count=Coalesce(Subquery(follows_subquery), 0),
            _uploads_count=Coalesce(Subquery(uploads_subquery), 0),
        )
    )
    serializer_class = serializers.ManageLibrarySerializer
    filterset_class = filters.ManageLibraryFilterSet
    required_scope = "instance:libraries"

    @rest_decorators.action(methods=["get"], detail=True)
    def stats(self, request, *args, **kwargs):
        library = self.get_object()
        uploads = library.uploads.all()
        tracks = uploads.values_list("track", flat=True).distinct()
        albums = (
            music_models.Track.objects.filter(pk__in=tracks)
            .values_list("album", flat=True)
            .distinct()
        )
        artists = set(
            music_models.Album.objects.filter(pk__in=albums).values_list(
                "artist", flat=True
            )
        ) | set(
            music_models.Track.objects.filter(pk__in=tracks).values_list(
                "artist", flat=True
            )
        )

        data = {
            "uploads": uploads.count(),
            "followers": library.received_follows.count(),
            "tracks": tracks.count(),
            "albums": albums.count(),
            "artists": len(artists),
            "reports": moderation_models.Report.objects.get_for_target(library).count(),
        }
        data.update(get_media_stats(uploads.all()))
        return response.Response(data, status=200)

    @rest_decorators.action(methods=["post"], detail=False)
    def action(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = serializers.ManageTrackActionSerializer(
            request.data, queryset=queryset
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return response.Response(result, status=200)


class ManageUploadViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "uuid"
    queryset = (
        music_models.Upload.objects.all()
        .order_by("-id")
        .select_related("library__actor", "track__artist", "track__album__artist")
    )
    serializer_class = serializers.ManageUploadSerializer
    filterset_class = filters.ManageUploadFilterSet
    required_scope = "instance:libraries"

    @rest_decorators.action(methods=["post"], detail=False)
    def action(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = serializers.ManageUploadActionSerializer(
            request.data, queryset=queryset
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return response.Response(result, status=200)


class ManageUserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = users_models.User.objects.all().select_related("actor").order_by("-id")
    serializer_class = serializers.ManageUserSerializer
    filterset_class = filters.ManageUserFilterSet
    required_scope = "instance:users"
    ordering_fields = ["date_joined", "last_activity", "username"]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["default_permissions"] = preferences.get("users__default_permissions")
        return context


class ManageInvitationViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = (
        users_models.Invitation.objects.all()
        .order_by("-id")
        .prefetch_related("users")
        .select_related("owner")
    )
    serializer_class = serializers.ManageInvitationSerializer
    filterset_class = filters.ManageInvitationFilterSet
    required_scope = "instance:invitations"
    ordering_fields = ["creation_date", "expiration_date"]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @rest_decorators.action(methods=["post"], detail=False)
    def action(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = serializers.ManageInvitationActionSerializer(
            request.data, queryset=queryset
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return response.Response(result, status=200)


class ManageDomainViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    lookup_value_regex = r"[a-zA-Z0-9\-\.]+"
    queryset = (
        federation_models.Domain.objects.with_actors_count()
        .with_outbox_activities_count()
        .prefetch_related("instance_policy")
        .order_by("name")
    )
    serializer_class = serializers.ManageDomainSerializer
    filterset_class = filters.ManageDomainFilterSet
    required_scope = "instance:domains"
    ordering_fields = [
        "name",
        "creation_date",
        "nodeinfo_fetch_date",
        "actors_count",
        "outbox_activities_count",
        "instance_policy",
    ]

    def get_queryset(self, **kwargs):
        queryset = super().get_queryset(**kwargs)
        return queryset.external()

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            # A dedicated serializer for update
            # to ensure domain name can't be changed
            return serializers.ManageDomainUpdateSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        domain = serializer.save()
        federation_tasks.update_domain_nodeinfo(domain_name=domain.name)

    @rest_decorators.action(methods=["get"], detail=True)
    def nodeinfo(self, request, *args, **kwargs):
        domain = self.get_object()
        federation_tasks.update_domain_nodeinfo(domain_name=domain.name)
        domain.refresh_from_db()
        return response.Response(domain.nodeinfo, status=200)

    @rest_decorators.action(methods=["get"], detail=True)
    def stats(self, request, *args, **kwargs):
        domain = self.get_object()
        return response.Response(domain.get_stats(), status=200)

    action = decorators.action_route(serializers.ManageDomainActionSerializer)


class ManageActorViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    lookup_value_regex = r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)"
    queryset = (
        federation_models.Actor.objects.all()
        .with_uploads_count()
        .order_by("-creation_date")
        .select_related("user")
        .prefetch_related("instance_policy")
    )
    serializer_class = serializers.ManageActorSerializer
    filterset_class = filters.ManageActorFilterSet
    required_scope = "instance:accounts"
    required_permissions = ["moderation"]
    ordering_fields = [
        "name",
        "preferred_username",
        "domain",
        "fid",
        "creation_date",
        "last_fetch_date",
        "uploads_count",
        "outbox_activities_count",
        "instance_policy",
    ]

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        username, domain = self.kwargs["pk"].split("@")
        filter_kwargs = {"domain_id": domain, "preferred_username": username}
        obj = get_object_or_404(queryset, **filter_kwargs)
        self.check_object_permissions(self.request, obj)

        return obj

    @rest_decorators.action(methods=["get"], detail=True)
    def stats(self, request, *args, **kwargs):
        obj = self.get_object()
        return response.Response(obj.get_stats(), status=200)

    action = decorators.action_route(serializers.ManageActorActionSerializer)


class ManageInstancePolicyViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = (
        moderation_models.InstancePolicy.objects.all()
        .order_by("-creation_date")
        .select_related()
    )
    serializer_class = serializers.ManageInstancePolicySerializer
    filterset_class = filters.ManageInstancePolicyFilterSet
    required_scope = "instance:policies"
    ordering_fields = ["id", "creation_date"]

    def perform_create(self, serializer):
        serializer.save(actor=self.request.user.actor)


class ManageReportViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "uuid"
    queryset = (
        moderation_models.Report.objects.all()
        .order_by("-creation_date")
        .select_related(
            "submitter", "target_owner", "assigned_to", "target_content_type"
        )
        .prefetch_related("target")
        .prefetch_related(
            Prefetch(
                "notes",
                queryset=moderation_models.Note.objects.order_by(
                    "creation_date"
                ).select_related("author"),
                to_attr="_prefetched_notes",
            )
        )
    )
    serializer_class = serializers.ManageReportSerializer
    filterset_class = filters.ManageReportFilterSet
    required_scope = "instance:reports"
    ordering_fields = ["id", "creation_date", "handled_date"]

    def perform_update(self, serializer):
        is_handled = serializer.instance.is_handled
        if not is_handled and serializer.validated_data.get("is_handled") is True:
            # report was resolved, we assign to the mod making the request
            serializer.save(assigned_to=self.request.user.actor)
        else:
            serializer.save()


class ManageNoteViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "uuid"
    queryset = (
        moderation_models.Note.objects.all()
        .order_by("-creation_date")
        .select_related("author", "target_content_type")
        .prefetch_related("target")
    )
    serializer_class = serializers.ManageNoteSerializer
    filterset_class = filters.ManageNoteFilterSet
    required_scope = "instance:notes"
    ordering_fields = ["id", "creation_date"]

    def perform_create(self, serializer):
        author = self.request.user.actor
        return serializer.save(author=author)


class ManageTagViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "name"
    queryset = (
        tags_models.Tag.objects.all()
        .order_by("-creation_date")
        .annotate(items_count=Count("tagged_items"))
        .annotate(length=Length("name"))
    )
    serializer_class = serializers.ManageTagSerializer
    filterset_class = filters.ManageTagFilterSet
    required_scope = "instance:libraries"
    ordering_fields = ["id", "creation_date", "name", "items_count", "length"]

    def get_queryset(self):
        queryset = super().get_queryset()
        from django.contrib.contenttypes.models import ContentType

        album_ct = ContentType.objects.get_for_model(music_models.Album)
        track_ct = ContentType.objects.get_for_model(music_models.Track)
        artist_ct = ContentType.objects.get_for_model(music_models.Artist)
        queryset = queryset.annotate(
            _albums_count=Count(
                "tagged_items", filter=Q(tagged_items__content_type=album_ct)
            ),
            _tracks_count=Count(
                "tagged_items", filter=Q(tagged_items__content_type=track_ct)
            ),
            _artists_count=Count(
                "tagged_items", filter=Q(tagged_items__content_type=artist_ct)
            ),
        )
        return queryset

    @rest_decorators.action(methods=["post"], detail=False)
    def action(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = serializers.ManageTagActionSerializer(
            request.data, queryset=queryset
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return response.Response(result, status=200)


class ManageUserRequestViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "uuid"
    queryset = (
        moderation_models.UserRequest.objects.all()
        .order_by("-creation_date")
        .select_related("submitter", "assigned_to")
        .prefetch_related(
            Prefetch(
                "notes",
                queryset=moderation_models.Note.objects.order_by(
                    "creation_date"
                ).select_related("author"),
                to_attr="_prefetched_notes",
            )
        )
    )
    serializer_class = serializers.ManageUserRequestSerializer
    filterset_class = filters.ManageUserRequestFilterSet
    required_scope = "instance:requests"
    ordering_fields = ["id", "creation_date", "handled_date"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action in ["update", "partial_update"]:
            # approved requests cannot be edited
            queryset = queryset.exclude(status="approved")
        return queryset

    @transaction.atomic
    def perform_update(self, serializer):
        old_status = serializer.instance.status
        new_status = serializer.validated_data.get("status")

        if old_status != new_status and new_status != "pending":
            # report was resolved, we assign to the mod making the request
            serializer.save(assigned_to=self.request.user.actor)
            common_utils.on_commit(
                moderation_tasks.user_request_handle.delay,
                user_request_id=serializer.instance.pk,
                new_status=new_status,
                old_status=old_status,
            )
        else:
            serializer.save()


class ManageChannelViewSet(
    MultipleLookupDetailMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):

    url_lookups = [
        {
            "lookup_field": "uuid",
            "validator": serializers.serializers.UUIDField().to_internal_value,
        },
        {
            "lookup_field": "username",
            "validator": federation_utils.get_actor_data_from_username,
            "get_query": lambda v: Q(
                actor__domain=v["domain"],
                actor__preferred_username__iexact=v["username"],
            ),
        },
    ]
    queryset = (
        audio_models.Channel.objects.all()
        .order_by("-id")
        .select_related("attributed_to", "actor",)
        .prefetch_related(
            Prefetch(
                "artist",
                queryset=(
                    music_models.Artist.objects.all()
                    .order_by("-id")
                    .select_related("attributed_to", "attachment_cover", "channel")
                    .annotate(_tracks_count=Count("tracks"))
                    .annotate(_albums_count=Count("albums"))
                    .prefetch_related(music_views.TAG_PREFETCH)
                ),
            )
        )
    )
    serializer_class = serializers.ManageChannelSerializer
    filterset_class = filters.ManageChannelFilterSet
    required_scope = "instance:libraries"
    ordering_fields = ["creation_date", "name"]

    @rest_decorators.action(methods=["get"], detail=True)
    def stats(self, request, *args, **kwargs):
        channel = self.get_object()
        tracks = music_models.Track.objects.filter(
            Q(artist=channel.artist) | Q(album__artist=channel.artist)
        )
        data = get_stats(tracks, channel, ignore_fields=["libraries", "channels"])
        data["follows"] = channel.actor.received_follows.count()
        return response.Response(data, status=200)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["description"] = self.action in ["retrieve", "create", "update"]
        return context

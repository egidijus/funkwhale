import base64
import datetime
import logging
import urllib.parse

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Prefetch, Sum, F, Q
import django.db.utils
from django.utils import timezone

from rest_framework import mixins
from rest_framework import settings as rest_settings
from rest_framework import views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from funkwhale_api.common import decorators as common_decorators
from funkwhale_api.common import permissions as common_permissions
from funkwhale_api.common import preferences
from funkwhale_api.common import utils as common_utils
from funkwhale_api.common import views as common_views
from funkwhale_api.federation.authentication import SignatureAuthentication
from funkwhale_api.federation import actors
from funkwhale_api.federation import api_serializers as federation_api_serializers
from funkwhale_api.federation import decorators as federation_decorators
from funkwhale_api.federation import models as federation_models
from funkwhale_api.federation import routes
from funkwhale_api.federation import tasks as federation_tasks
from funkwhale_api.tags.models import Tag, TaggedItem
from funkwhale_api.tags.serializers import TagSerializer
from funkwhale_api.users.oauth import permissions as oauth_permissions
from funkwhale_api.users.authentication import ScopedTokenAuthentication

from . import filters, licenses, models, serializers, tasks, utils

logger = logging.getLogger(__name__)

TAG_PREFETCH = Prefetch(
    "tagged_items",
    queryset=TaggedItem.objects.all().select_related().order_by("tag__name"),
    to_attr="_prefetched_tagged_items",
)


def get_libraries(filter_uploads):
    def libraries(self, request, *args, **kwargs):
        obj = self.get_object()
        actor = utils.get_actor_from_request(request)
        uploads = models.Upload.objects.all()
        uploads = filter_uploads(obj, uploads)
        uploads = uploads.playable_by(actor)
        qs = models.Library.objects.filter(
            pk__in=uploads.values_list("library", flat=True), channel=None,
        ).annotate(_uploads_count=Count("uploads"))
        qs = qs.prefetch_related("actor")
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = federation_api_serializers.LibrarySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = federation_api_serializers.LibrarySerializer(qs, many=True)
        return Response(serializer.data)

    return libraries


def refetch_obj(obj, queryset):
    """
    Given an Artist/Album/Track instance, if the instance is from a remote pod,
    will attempt to update local data with the latest ActivityPub representation.
    """
    if obj.is_local:
        return obj

    now = timezone.now()
    limit = now - datetime.timedelta(minutes=settings.FEDERATION_OBJECT_FETCH_DELAY)
    last_fetch = obj.fetches.order_by("-creation_date").first()
    if last_fetch is not None and last_fetch.creation_date > limit:
        # we fetched recently, no need to do it again
        return obj

    logger.info("Refetching %s:%s at %s…", obj._meta.label, obj.pk, obj.fid)
    actor = actors.get_service_actor()
    fetch = federation_models.Fetch.objects.create(actor=actor, url=obj.fid, object=obj)
    try:
        federation_tasks.fetch(fetch_id=fetch.pk)
    except Exception:
        logger.exception(
            "Error while refetching %s:%s at %s…", obj._meta.label, obj.pk, obj.fid
        )
    else:
        fetch.refresh_from_db()
        if fetch.status == "finished":
            obj = queryset.get(pk=obj.pk)
    return obj


class HandleInvalidSearch(object):
    def list(self, *args, **kwargs):
        try:
            return super().list(*args, **kwargs)
        except django.db.utils.ProgrammingError as e:
            if "in tsquery:" in str(e):
                return Response({"detail": "Invalid query"}, status=400)
            else:
                raise


class ArtistViewSet(
    HandleInvalidSearch,
    common_views.SkipFilterForGetObject,
    viewsets.ReadOnlyModelViewSet,
):
    queryset = (
        models.Artist.objects.all()
        .prefetch_related("attributed_to", "attachment_cover")
        .prefetch_related(
            "channel__actor",
            Prefetch(
                "tracks",
                queryset=models.Track.objects.all(),
                to_attr="_prefetched_tracks",
            ),
        )
        .order_by("-id")
    )
    serializer_class = serializers.ArtistWithAlbumsSerializer
    permission_classes = [oauth_permissions.ScopePermission]
    required_scope = "libraries"
    anonymous_policy = "setting"
    filterset_class = filters.ArtistFilter
    ordering_fields = ("id", "name", "creation_date", "modification_date")

    fetches = federation_decorators.fetches_route()
    mutations = common_decorators.mutations_route(types=["update"])

    def get_object(self):
        obj = super().get_object()

        if (
            self.action == "retrieve"
            and self.request.GET.get("refresh", "").lower() == "true"
        ):
            obj = refetch_obj(obj, self.get_queryset())
        return obj

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["description"] = self.action in ["retrieve", "create", "update"]
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        albums = models.Album.objects.with_tracks_count().select_related(
            "attachment_cover"
        )
        albums = albums.annotate_playable_by_actor(
            utils.get_actor_from_request(self.request)
        )
        return queryset.prefetch_related(
            Prefetch("albums", queryset=albums), TAG_PREFETCH
        )

    libraries = action(methods=["get"], detail=True)(
        get_libraries(
            filter_uploads=lambda o, uploads: uploads.filter(
                Q(track__artist=o) | Q(track__album__artist=o)
            )
        )
    )


class AlbumViewSet(
    HandleInvalidSearch,
    common_views.SkipFilterForGetObject,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    queryset = (
        models.Album.objects.all()
        .order_by("-creation_date")
        .prefetch_related("artist", "attributed_to", "attachment_cover")
    )
    serializer_class = serializers.AlbumSerializer
    permission_classes = [oauth_permissions.ScopePermission]
    required_scope = "libraries"
    anonymous_policy = "setting"
    ordering_fields = (
        "creation_date",
        "release_date",
        "title",
        "artist__modification_date",
    )
    filterset_class = filters.AlbumFilter

    fetches = federation_decorators.fetches_route()
    mutations = common_decorators.mutations_route(types=["update"])

    def get_object(self):
        obj = super().get_object()

        if (
            self.action == "retrieve"
            and self.request.GET.get("refresh", "").lower() == "true"
        ):
            obj = refetch_obj(obj, self.get_queryset())
        return obj

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["description"] = self.action in [
            "retrieve",
            "create",
        ]
        context["user"] = self.request.user
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action in ["destroy"]:
            queryset = queryset.exclude(artist__channel=None).filter(
                artist__attributed_to=self.request.user.actor
            )
        tracks = (
            models.Track.objects.prefetch_related("artist")
            .with_playable_uploads(utils.get_actor_from_request(self.request))
            .order_for_album()
        )
        qs = queryset.prefetch_related(
            Prefetch("tracks", queryset=tracks), TAG_PREFETCH
        )
        return qs

    libraries = action(methods=["get"], detail=True)(
        get_libraries(filter_uploads=lambda o, uploads: uploads.filter(track__album=o))
    )

    def get_serializer_class(self):
        if self.action in ["create"]:
            return serializers.AlbumCreateSerializer
        return super().get_serializer_class()

    @transaction.atomic
    def perform_destroy(self, instance):
        routes.outbox.dispatch(
            {"type": "Delete", "object": {"type": "Album"}},
            context={"album": instance},
        )
        models.Album.objects.filter(pk=instance.pk).delete()


class LibraryViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "uuid"
    queryset = (
        models.Library.objects.all()
        .filter(channel=None)
        .select_related("actor")
        .order_by("-creation_date")
        .annotate(_uploads_count=Count("uploads"))
        .annotate(_size=Sum("uploads__size"))
    )
    serializer_class = serializers.LibraryForOwnerSerializer
    permission_classes = [
        oauth_permissions.ScopePermission,
        common_permissions.OwnerPermission,
    ]
    filterset_class = filters.LibraryFilter
    required_scope = "libraries"
    anonymous_policy = "setting"
    owner_field = "actor.user"
    owner_checks = ["write"]

    def get_queryset(self):
        qs = super().get_queryset()
        # allow retrieving a single library by uuid if request.user isn't
        # the owner. Any other get should be from the owner only
        if self.action not in ["retrieve", "list"]:
            qs = qs.filter(actor=self.request.user.actor)
        if self.action == "list":
            actor = utils.get_actor_from_request(self.request)
            qs = qs.viewable_by(actor)

        return qs

    def perform_create(self, serializer):
        serializer.save(actor=self.request.user.actor)

    @transaction.atomic
    def perform_destroy(self, instance):
        routes.outbox.dispatch(
            {"type": "Delete", "object": {"type": "Library"}},
            context={"library": instance},
        )
        instance.delete()

    follows = action

    @action(methods=["get"], detail=True)
    @transaction.non_atomic_requests
    def follows(self, request, *args, **kwargs):
        library = self.get_object()
        queryset = (
            library.received_follows.filter(target__actor=self.request.user.actor)
            .prefetch_related("actor", "target__actor")
            .order_by("-creation_date")
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = federation_api_serializers.LibraryFollowSerializer(
                page, many=True
            )
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class TrackViewSet(
    HandleInvalidSearch,
    common_views.SkipFilterForGetObject,
    mixins.DestroyModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """
    A simple ViewSet for viewing and editing accounts.
    """

    queryset = (
        models.Track.objects.all()
        .for_nested_serialization()
        .prefetch_related("attributed_to", "attachment_cover")
        .order_by("-creation_date")
    )
    serializer_class = serializers.TrackSerializer
    permission_classes = [oauth_permissions.ScopePermission]
    required_scope = "libraries"
    anonymous_policy = "setting"
    filterset_class = filters.TrackFilter
    ordering_fields = (
        "creation_date",
        "title",
        "album__title",
        "album__release_date",
        "size",
        "position",
        "disc_number",
        "artist__name",
        "artist__modification_date",
    )
    fetches = federation_decorators.fetches_route()
    mutations = common_decorators.mutations_route(types=["update"])

    def get_object(self):
        obj = super().get_object()

        if (
            self.action == "retrieve"
            and self.request.GET.get("refresh", "").lower() == "true"
        ):
            obj = refetch_obj(obj, self.get_queryset())
        return obj

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action in ["destroy"]:
            queryset = queryset.exclude(artist__channel=None).filter(
                artist__attributed_to=self.request.user.actor
            )
        filter_favorites = self.request.GET.get("favorites", None)
        user = self.request.user
        if user.is_authenticated and filter_favorites == "true":
            queryset = queryset.filter(track_favorites__user=user)

        queryset = queryset.with_playable_uploads(
            utils.get_actor_from_request(self.request)
        )
        return queryset.prefetch_related(TAG_PREFETCH)

    libraries = action(methods=["get"], detail=True)(
        get_libraries(filter_uploads=lambda o, uploads: uploads.filter(track=o))
    )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["description"] = self.action in ["retrieve", "create", "update"]
        return context

    @transaction.atomic
    def perform_destroy(self, instance):
        uploads = instance.uploads.order_by("id")
        routes.outbox.dispatch(
            {"type": "Delete", "object": {"type": "Audio"}},
            context={"uploads": list(uploads)},
        )
        instance.delete()


def strip_absolute_media_url(path):
    if (
        settings.MEDIA_URL.startswith("http://")
        or settings.MEDIA_URL.startswith("https://")
        and path.startswith(settings.MEDIA_URL)
    ):
        path = path.replace(settings.MEDIA_URL, "/media/", 1)
    return path


def get_file_path(audio_file):
    serve_path = settings.MUSIC_DIRECTORY_SERVE_PATH
    prefix = settings.MUSIC_DIRECTORY_PATH
    t = settings.REVERSE_PROXY_TYPE
    if t == "nginx":
        # we have to use the internal locations
        try:
            path = audio_file.url
        except AttributeError:
            # a path was given
            if not serve_path or not prefix:
                raise ValueError(
                    "You need to specify MUSIC_DIRECTORY_SERVE_PATH and "
                    "MUSIC_DIRECTORY_PATH to serve in-place imported files"
                )
            path = "/music" + audio_file.replace(prefix, "", 1)
        path = strip_absolute_media_url(path)
        if path.startswith("http://") or path.startswith("https://"):
            protocol, remainder = path.split("://", 1)
            hostname, r_path = remainder.split("/", 1)
            r_path = urllib.parse.quote(r_path)
            path = protocol + "://" + hostname + "/" + r_path
            return (settings.PROTECT_FILES_PATH + "/media/" + path).encode("utf-8")
        # needed to serve files with % or ? chars
        path = urllib.parse.quote(path)
        return (settings.PROTECT_FILES_PATH + path).encode("utf-8")
    if t == "apache2":
        try:
            path = audio_file.path
        except AttributeError:
            # a path was given
            if not serve_path or not prefix:
                raise ValueError(
                    "You need to specify MUSIC_DIRECTORY_SERVE_PATH and "
                    "MUSIC_DIRECTORY_PATH to serve in-place imported files"
                )
            path = audio_file.replace(prefix, serve_path, 1)
        path = strip_absolute_media_url(path)
        return path.encode("utf-8")


def should_transcode(upload, format, max_bitrate=None):
    if not preferences.get("music__transcoding_enabled"):
        return False
    format_need_transcoding = True
    bitrate_need_transcoding = True
    if format is None:
        format_need_transcoding = False
    elif format not in utils.EXTENSION_TO_MIMETYPE:
        # format should match supported formats
        format_need_transcoding = False
    elif upload.mimetype is None:
        # upload should have a mimetype, otherwise we cannot transcode
        format_need_transcoding = False
    elif upload.mimetype == utils.EXTENSION_TO_MIMETYPE[format]:
        # requested format sould be different than upload mimetype, otherwise
        # there is no need to transcode
        format_need_transcoding = False

    if max_bitrate is None:
        bitrate_need_transcoding = False
    elif not upload.bitrate:
        bitrate_need_transcoding = False
    elif upload.bitrate <= max_bitrate:
        bitrate_need_transcoding = False

    return format_need_transcoding or bitrate_need_transcoding


def get_content_disposition(filename):
    filename = "filename*=UTF-8''{}".format(urllib.parse.quote(filename))
    return "attachment; {}".format(filename)


def record_downloads(f):
    def inner(*args, **kwargs):
        user = kwargs.get("user")
        wsgi_request = kwargs.pop("wsgi_request")
        upload = kwargs.get("upload")
        response = f(*args, **kwargs)
        if response.status_code >= 200 and response.status_code < 400:
            utils.increment_downloads_count(
                upload=upload, user=user, wsgi_request=wsgi_request
            )

        return response

    return inner


@record_downloads
def handle_serve(
    upload, user, format=None, max_bitrate=None, proxy_media=True, download=True
):
    f = upload
    # we update the accessed_date
    now = timezone.now()
    upload.accessed_date = now
    upload.save(update_fields=["accessed_date"])
    f = upload
    if f.audio_file:
        file_path = get_file_path(f.audio_file)

    elif f.source and (
        f.source.startswith("http://") or f.source.startswith("https://")
    ):
        # we need to populate from cache
        with transaction.atomic():
            # why the transaction/select_for_update?
            # this is because browsers may send multiple requests
            # in a short time range, for partial content,
            # thus resulting in multiple downloads from the remote
            qs = f.__class__.objects.select_for_update()
            f = qs.get(pk=f.pk)
            if user.is_authenticated:
                actor = user.actor
            else:
                actor = actors.get_service_actor()
            f.download_audio_from_remote(actor=actor)
        data = f.get_audio_data()
        if data:
            f.duration = data["duration"]
            f.size = data["size"]
            f.bitrate = data["bitrate"]
            f.save(update_fields=["bitrate", "duration", "size"])
        file_path = get_file_path(f.audio_file)
    elif f.source and f.source.startswith("file://"):
        file_path = get_file_path(f.source.replace("file://", "", 1))
    mt = f.mimetype

    if should_transcode(f, format, max_bitrate=max_bitrate):
        transcoded_version = f.get_transcoded_version(format, max_bitrate=max_bitrate)
        transcoded_version.accessed_date = now
        transcoded_version.save(update_fields=["accessed_date"])
        f = transcoded_version
        file_path = get_file_path(f.audio_file)
        mt = f.mimetype
    if not proxy_media and f.audio_file:
        # we simply issue a 302 redirect to the real URL
        response = Response(status=302)
        response["Location"] = f.audio_file.url
        return response
    if mt:
        response = Response(content_type=mt)
    else:
        response = Response()
    filename = f.filename
    mapping = {"nginx": "X-Accel-Redirect", "apache2": "X-Sendfile"}
    file_header = mapping[settings.REVERSE_PROXY_TYPE]
    response[file_header] = file_path
    if download:
        response["Content-Disposition"] = get_content_disposition(filename)
    if mt:
        response["Content-Type"] = mt

    return response


class ListenViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = models.Track.objects.all()
    serializer_class = serializers.TrackSerializer
    authentication_classes = (
        rest_settings.api_settings.DEFAULT_AUTHENTICATION_CLASSES
        + [SignatureAuthentication, ScopedTokenAuthentication]
    )
    permission_classes = [oauth_permissions.ScopePermission]
    required_scope = "libraries"
    anonymous_policy = "setting"
    lookup_field = "uuid"

    def retrieve(self, request, *args, **kwargs):
        track = self.get_object()
        actor = utils.get_actor_from_request(request)
        queryset = track.uploads.prefetch_related(
            "track__album__artist", "track__artist"
        )
        explicit_file = request.GET.get("upload")
        download = request.GET.get("download", "true").lower() == "true"
        if explicit_file:
            queryset = queryset.filter(uuid=explicit_file)
        queryset = queryset.playable_by(actor)
        queryset = queryset.order_by(F("audio_file").desc(nulls_last=True))
        upload = queryset.first()
        if not upload:
            return Response(status=404)

        format = request.GET.get("to")
        max_bitrate = request.GET.get("max_bitrate")
        try:
            max_bitrate = min(max(int(max_bitrate), 0), 320) or None
        except (TypeError, ValueError):
            max_bitrate = None

        if max_bitrate:
            max_bitrate = max_bitrate * 1000
        return handle_serve(
            upload=upload,
            user=request.user,
            format=format,
            max_bitrate=max_bitrate,
            proxy_media=settings.PROXY_MEDIA,
            download=download,
            wsgi_request=request._request,
        )


class UploadViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "uuid"
    queryset = (
        models.Upload.objects.all()
        .order_by("-creation_date")
        .prefetch_related(
            "library__actor",
            "track__artist",
            "track__album__artist",
            "track__attachment_cover",
        )
    )
    serializer_class = serializers.UploadForOwnerSerializer
    permission_classes = [
        oauth_permissions.ScopePermission,
        common_permissions.OwnerPermission,
    ]
    required_scope = "libraries"
    anonymous_policy = "setting"
    owner_field = "library.actor.user"
    owner_checks = ["write"]
    filterset_class = filters.UploadFilter
    ordering_fields = (
        "creation_date",
        "import_date",
        "bitrate",
        "size",
        "artist__name",
    )

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action in ["update", "partial_update"]:
            # prevent updating an upload that is already processed
            qs = qs.filter(import_status="draft")
        if self.action != "retrieve":
            qs = qs.filter(library__actor=self.request.user.actor)
        else:
            actor = utils.get_actor_from_request(self.request)
            qs = qs.playable_by(actor)
        return qs

    @action(methods=["get"], detail=True, url_path="audio-file-metadata")
    def audio_file_metadata(self, request, *args, **kwargs):
        upload = self.get_object()
        try:
            m = tasks.metadata.Metadata(upload.get_audio_file())
        except FileNotFoundError:
            return Response({"detail": "File not found"}, status=500)
        serializer = tasks.metadata.TrackMetadataSerializer(
            data=m, context={"strict": False}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=500)
        payload = serializer.validated_data
        cover_data = payload.get(
            "cover_data", payload.get("album", {}).get("cover_data", {})
        )
        if cover_data and "content" in cover_data:
            cover_data["content"] = base64.b64encode(cover_data["content"])
        return Response(payload, status=200)

    @action(methods=["post"], detail=False)
    def action(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = serializers.UploadActionSerializer(request.data, queryset=queryset)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=200)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["user"] = self.request.user
        return context

    def perform_create(self, serializer):
        upload = serializer.save()
        if upload.import_status == "pending":
            common_utils.on_commit(tasks.process_upload.delay, upload_id=upload.pk)

    def perform_update(self, serializer):
        upload = serializer.save()
        if upload.import_status == "pending":
            common_utils.on_commit(tasks.process_upload.delay, upload_id=upload.pk)

    @transaction.atomic
    def perform_destroy(self, instance):
        routes.outbox.dispatch(
            {"type": "Delete", "object": {"type": "Audio"}},
            context={"uploads": [instance]},
        )
        instance.delete()


class Search(views.APIView):
    max_results = 3
    permission_classes = [oauth_permissions.ScopePermission]
    required_scope = "libraries"
    anonymous_policy = "setting"

    def get(self, request, *args, **kwargs):
        query = request.GET.get("query", request.GET.get("q", "")) or ""
        query = query.strip()
        if not query:
            return Response({"detail": "empty query"}, status=400)
        try:
            results = {
                # 'tags': serializers.TagSerializer(self.get_tags(query), many=True).data,
                "artists": serializers.ArtistWithAlbumsSerializer(
                    self.get_artists(query), many=True
                ).data,
                "tracks": serializers.TrackSerializer(
                    self.get_tracks(query), many=True
                ).data,
                "albums": serializers.AlbumSerializer(
                    self.get_albums(query), many=True
                ).data,
                "tags": TagSerializer(self.get_tags(query), many=True).data,
            }
        except django.db.utils.ProgrammingError as e:
            if "in tsquery:" in str(e):
                return Response({"detail": "Invalid query"}, status=400)
            else:
                raise

        return Response(results, status=200)

    def get_tracks(self, query):
        search_fields = [
            "mbid",
            "title__unaccent",
            "album__title__unaccent",
            "artist__name__unaccent",
        ]
        if settings.USE_FULL_TEXT_SEARCH:
            query_obj = utils.get_fts_query(
                query,
                fts_fields=["body_text", "album__body_text", "artist__body_text"],
                model=models.Track,
            )
        else:
            query_obj = utils.get_query(query, search_fields)
        qs = (
            models.Track.objects.all()
            .filter(query_obj)
            .prefetch_related(
                "artist",
                "attributed_to",
                Prefetch(
                    "album",
                    queryset=models.Album.objects.select_related(
                        "artist", "attachment_cover", "attributed_to"
                    ),
                ),
            )
        )
        return common_utils.order_for_search(qs, "title")[: self.max_results]

    def get_albums(self, query):
        search_fields = ["mbid", "title__unaccent", "artist__name__unaccent"]
        if settings.USE_FULL_TEXT_SEARCH:
            query_obj = utils.get_fts_query(
                query, fts_fields=["body_text", "artist__body_text"], model=models.Album
            )
        else:
            query_obj = utils.get_query(query, search_fields)
        qs = (
            models.Album.objects.all()
            .filter(query_obj)
            .select_related("artist", "attachment_cover", "attributed_to")
            .prefetch_related("tracks__artist")
        )
        return common_utils.order_for_search(qs, "title")[: self.max_results]

    def get_artists(self, query):
        search_fields = ["mbid", "name__unaccent"]
        if settings.USE_FULL_TEXT_SEARCH:
            query_obj = utils.get_fts_query(query, model=models.Artist)
        else:
            query_obj = utils.get_query(query, search_fields)
        qs = (
            models.Artist.objects.all()
            .filter(query_obj)
            .with_albums()
            .prefetch_related("channel__actor")
            .select_related("attributed_to")
        )
        return common_utils.order_for_search(qs, "name")[: self.max_results]

    def get_tags(self, query):
        search_fields = ["name__unaccent"]
        query_obj = utils.get_query(query, search_fields)
        qs = Tag.objects.all().filter(query_obj)
        return common_utils.order_for_search(qs, "name")[: self.max_results]


class LicenseViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [oauth_permissions.ScopePermission]
    required_scope = "libraries"
    anonymous_policy = "setting"
    serializer_class = serializers.LicenseSerializer
    queryset = models.License.objects.all().order_by("code")
    lookup_value_regex = ".*"
    max_page_size = 1000

    def get_queryset(self):
        # ensure our licenses are up to date in DB
        licenses.load(licenses.LICENSES)
        return super().get_queryset()

    def get_serializer(self, *args, **kwargs):
        if len(args) == 0:
            return super().get_serializer(*args, **kwargs)

        # our serializer works with license dict, not License instances
        # so we pass those instead
        instance_or_qs = args[0]
        try:
            first_arg = instance_or_qs.conf
        except AttributeError:
            first_arg = [i.conf for i in instance_or_qs if i.conf]
        return super().get_serializer(*((first_arg,) + args[1:]), **kwargs)


class OembedView(views.APIView):
    permission_classes = [oauth_permissions.ScopePermission]
    required_scope = "libraries"
    anonymous_policy = "setting"

    def get(self, request, *args, **kwargs):
        serializer = serializers.OembedSerializer(data=request.GET)
        serializer.is_valid(raise_exception=True)
        embed_data = serializer.save()
        return Response(embed_data)

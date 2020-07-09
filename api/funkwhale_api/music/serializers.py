import urllib.parse

from django.db import transaction
from django import urls
from django.conf import settings
from rest_framework import serializers

from funkwhale_api.activity import serializers as activity_serializers
from funkwhale_api.common import models as common_models
from funkwhale_api.common import serializers as common_serializers
from funkwhale_api.common import utils as common_utils
from funkwhale_api.federation import routes
from funkwhale_api.federation import utils as federation_utils
from funkwhale_api.playlists import models as playlists_models
from funkwhale_api.tags import models as tag_models
from funkwhale_api.tags import serializers as tags_serializers

from . import filters, models, tasks, utils

NOOP = object()

COVER_WRITE_FIELD = common_serializers.RelatedField(
    "uuid",
    queryset=common_models.Attachment.objects.all().local(),
    serializer=None,
    allow_null=True,
    required=False,
    queryset_filter=lambda qs, context: qs.filter(actor=context["request"].user.actor),
    write_only=True,
)

from funkwhale_api.audio import serializers as audio_serializers  # NOQA


class CoverField(
    common_serializers.NullToEmptDict, common_serializers.AttachmentSerializer
):
    # XXX: BACKWARD COMPATIBILITY
    pass


cover_field = CoverField()


def serialize_attributed_to(self, obj):
    # Import at runtime to avoid a circular import issue
    from funkwhale_api.federation import serializers as federation_serializers

    if not obj.attributed_to_id:
        return

    return federation_serializers.APIActorSerializer(obj.attributed_to).data


class OptionalDescriptionMixin(object):
    def to_representation(self, obj):
        repr = super().to_representation(obj)
        if self.context.get("description", False):
            description = obj.description
            repr["description"] = (
                common_serializers.ContentSerializer(description).data
                if description
                else None
            )

        return repr


class LicenseSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    url = serializers.URLField()
    code = serializers.CharField()
    name = serializers.CharField()
    redistribute = serializers.BooleanField()
    derivative = serializers.BooleanField()
    commercial = serializers.BooleanField()
    attribution = serializers.BooleanField()
    copyleft = serializers.BooleanField()

    def get_id(self, obj):
        return obj["identifiers"][0]

    class Meta:
        model = models.License


class ArtistAlbumSerializer(serializers.Serializer):
    tracks_count = serializers.SerializerMethodField()
    cover = cover_field
    is_playable = serializers.SerializerMethodField()
    is_local = serializers.BooleanField()
    id = serializers.IntegerField()
    fid = serializers.URLField()
    mbid = serializers.UUIDField()
    title = serializers.CharField()
    artist = serializers.SerializerMethodField()
    release_date = serializers.DateField()
    creation_date = serializers.DateTimeField()

    def get_artist(self, o):
        return o.artist_id

    def get_tracks_count(self, o):
        return len(o.tracks.all())

    def get_is_playable(self, obj):
        try:
            return bool(obj.is_playable_by_actor)
        except AttributeError:
            return None


DATETIME_FIELD = serializers.DateTimeField()


class ArtistWithAlbumsSerializer(OptionalDescriptionMixin, serializers.Serializer):
    albums = ArtistAlbumSerializer(many=True)
    tags = serializers.SerializerMethodField()
    attributed_to = serializers.SerializerMethodField()
    channel = serializers.SerializerMethodField()
    tracks_count = serializers.SerializerMethodField()
    id = serializers.IntegerField()
    fid = serializers.URLField()
    mbid = serializers.UUIDField()
    name = serializers.CharField()
    content_category = serializers.CharField()
    creation_date = serializers.DateTimeField()
    is_local = serializers.BooleanField()
    cover = cover_field

    def get_tags(self, obj):
        tagged_items = getattr(obj, "_prefetched_tagged_items", [])
        return [ti.tag.name for ti in tagged_items]

    get_attributed_to = serialize_attributed_to

    def get_tracks_count(self, o):
        tracks = getattr(o, "_prefetched_tracks", None)
        return len(tracks) if tracks else None

    def get_channel(self, o):
        channel = o.get_channel()
        if not channel:
            return

        return {
            "uuid": str(channel.uuid),
            "actor": {
                "full_username": channel.actor.full_username,
                "preferred_username": channel.actor.preferred_username,
                "domain": channel.actor.domain_id,
            },
        }


def serialize_artist_simple(artist):
    data = {
        "id": artist.id,
        "fid": artist.fid,
        "mbid": str(artist.mbid),
        "name": artist.name,
        "creation_date": DATETIME_FIELD.to_representation(artist.creation_date),
        "modification_date": DATETIME_FIELD.to_representation(artist.modification_date),
        "is_local": artist.is_local,
        "content_category": artist.content_category,
    }
    if "description" in artist._state.fields_cache:
        data["description"] = (
            common_serializers.ContentSerializer(artist.description).data
            if artist.description
            else None
        )

    if "attachment_cover" in artist._state.fields_cache:
        data["cover"] = (
            cover_field.to_representation(artist.attachment_cover)
            if artist.attachment_cover
            else None
        )

    if getattr(artist, "_tracks_count", None) is not None:
        data["tracks_count"] = artist._tracks_count

    if getattr(artist, "_prefetched_tagged_items", None) is not None:
        data["tags"] = [ti.tag.name for ti in artist._prefetched_tagged_items]

    return data


class AlbumSerializer(OptionalDescriptionMixin, serializers.Serializer):
    artist = serializers.SerializerMethodField()
    cover = cover_field
    is_playable = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    tracks_count = serializers.SerializerMethodField()
    attributed_to = serializers.SerializerMethodField()
    id = serializers.IntegerField()
    fid = serializers.URLField()
    mbid = serializers.UUIDField()
    title = serializers.CharField()
    artist = serializers.SerializerMethodField()
    release_date = serializers.DateField()
    creation_date = serializers.DateTimeField()
    is_local = serializers.BooleanField()
    is_playable = serializers.SerializerMethodField()

    get_attributed_to = serialize_attributed_to

    def get_artist(self, o):
        return serialize_artist_simple(o.artist)

    def get_tracks_count(self, o):
        return len(o.tracks.all())

    def get_is_playable(self, obj):
        try:
            return any(
                [bool(getattr(t, "playable_uploads", [])) for t in obj.tracks.all()]
            )
        except AttributeError:
            return None

    def get_tags(self, obj):
        tagged_items = getattr(obj, "_prefetched_tagged_items", [])
        return [ti.tag.name for ti in tagged_items]


class TrackAlbumSerializer(serializers.ModelSerializer):
    artist = serializers.SerializerMethodField()
    cover = cover_field

    class Meta:
        model = models.Album
        fields = (
            "id",
            "fid",
            "mbid",
            "title",
            "artist",
            "release_date",
            "cover",
            "creation_date",
            "is_local",
        )

    def get_artist(self, o):
        return serialize_artist_simple(o.artist)


def serialize_upload(upload):
    return {
        "uuid": str(upload.uuid),
        "listen_url": upload.listen_url,
        "size": upload.size,
        "duration": upload.duration,
        "bitrate": upload.bitrate,
        "mimetype": upload.mimetype,
        "extension": upload.extension,
    }


def sort_uploads_for_listen(uploads):
    """
    Given a list of uploads, return a sorted list of uploads, with local or locally
    cached ones first, and older first
    """
    score = {upload: 0 for upload in uploads}
    for upload in uploads:
        if upload.is_local:
            score[upload] = 3
        elif upload.audio_file:
            score[upload] = 2

    sorted_tuples = sorted(score.items(), key=lambda t: (t[1], -t[0].pk), reverse=True)
    return [t[0] for t in sorted_tuples]


class TrackSerializer(OptionalDescriptionMixin, serializers.Serializer):
    artist = serializers.SerializerMethodField()
    album = TrackAlbumSerializer(read_only=True)
    uploads = serializers.SerializerMethodField()
    listen_url = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    attributed_to = serializers.SerializerMethodField()

    id = serializers.IntegerField()
    fid = serializers.URLField()
    mbid = serializers.UUIDField()
    title = serializers.CharField()
    artist = serializers.SerializerMethodField()
    creation_date = serializers.DateTimeField()
    is_local = serializers.BooleanField()
    position = serializers.IntegerField()
    disc_number = serializers.IntegerField()
    copyright = serializers.CharField()
    license = serializers.SerializerMethodField()
    cover = cover_field
    get_attributed_to = serialize_attributed_to

    def get_artist(self, o):
        return serialize_artist_simple(o.artist)

    def get_listen_url(self, obj):
        return obj.listen_url

    def get_uploads(self, obj):
        uploads = getattr(obj, "playable_uploads", [])
        return [serialize_upload(u) for u in sort_uploads_for_listen(uploads)]

    def get_tags(self, obj):
        tagged_items = getattr(obj, "_prefetched_tagged_items", [])
        return [ti.tag.name for ti in tagged_items]

    def get_license(self, o):
        return o.license_id


@common_serializers.track_fields_for_update("name", "description", "privacy_level")
class LibraryForOwnerSerializer(serializers.ModelSerializer):
    uploads_count = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    actor = serializers.SerializerMethodField()

    class Meta:
        model = models.Library
        fields = [
            "uuid",
            "fid",
            "name",
            "description",
            "privacy_level",
            "uploads_count",
            "size",
            "creation_date",
            "actor",
        ]
        read_only_fields = ["fid", "uuid", "creation_date", "actor"]

    def get_uploads_count(self, o):
        return getattr(o, "_uploads_count", o.uploads_count)

    def get_size(self, o):
        return getattr(o, "_size", 0)

    def on_updated_fields(self, obj, before, after):
        routes.outbox.dispatch(
            {"type": "Update", "object": {"type": "Library"}}, context={"library": obj}
        )

    def get_actor(self, o):
        # Import at runtime to avoid a circular import issue
        from funkwhale_api.federation import serializers as federation_serializers

        return federation_serializers.APIActorSerializer(o.actor).data


class UploadSerializer(serializers.ModelSerializer):
    track = TrackSerializer(required=False, allow_null=True)
    library = common_serializers.RelatedField(
        "uuid",
        LibraryForOwnerSerializer(),
        required=False,
        filters=lambda context: {"actor": context["user"].actor},
    )
    channel = common_serializers.RelatedField(
        "uuid",
        audio_serializers.ChannelSerializer(),
        required=False,
        filters=lambda context: {"attributed_to": context["user"].actor},
    )

    class Meta:
        model = models.Upload
        fields = [
            "uuid",
            "filename",
            "creation_date",
            "mimetype",
            "track",
            "library",
            "channel",
            "duration",
            "mimetype",
            "bitrate",
            "size",
            "import_date",
            "import_status",
        ]

        read_only_fields = [
            "uuid",
            "creation_date",
            "duration",
            "mimetype",
            "bitrate",
            "size",
            "track",
            "import_date",
        ]

    def validate(self, data):
        validated_data = super().validate(data)
        if "audio_file" in validated_data:
            audio_data = utils.get_audio_file_data(validated_data["audio_file"])
            if audio_data:
                validated_data["duration"] = audio_data["length"]
                validated_data["bitrate"] = audio_data["bitrate"]
        return validated_data


def filter_album(qs, context):
    if "channel" in context:
        return qs.filter(artist__channel=context["channel"])
    if "actor" in context:
        return qs.filter(artist__attributed_to=context["actor"])

    return qs.none()


class ImportMetadataSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=500, required=True)
    description = serializers.CharField(
        max_length=5000, required=False, allow_null=True
    )
    mbid = serializers.UUIDField(required=False, allow_null=True)
    copyright = serializers.CharField(max_length=500, required=False, allow_null=True)
    position = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    tags = tags_serializers.TagsListField(required=False)
    license = common_serializers.RelatedField(
        "code", LicenseSerializer(), required=False, allow_null=True
    )
    cover = common_serializers.RelatedField(
        "uuid",
        queryset=common_models.Attachment.objects.all().local(),
        serializer=None,
        queryset_filter=lambda qs, context: qs.filter(actor=context["actor"]),
        write_only=True,
        required=False,
        allow_null=True,
    )
    album = common_serializers.RelatedField(
        "id",
        queryset=models.Album.objects.all(),
        serializer=None,
        queryset_filter=filter_album,
        write_only=True,
        required=False,
        allow_null=True,
    )


class ImportMetadataField(serializers.JSONField):
    def to_internal_value(self, v):
        v = super().to_internal_value(v)
        s = ImportMetadataSerializer(
            data=v, context={"actor": self.context["user"].actor}
        )
        s.is_valid(raise_exception=True)
        return v


class UploadForOwnerSerializer(UploadSerializer):
    import_status = serializers.ChoiceField(
        choices=["draft", "pending"], default="pending"
    )
    import_metadata = ImportMetadataField(required=False)

    class Meta(UploadSerializer.Meta):
        fields = UploadSerializer.Meta.fields + [
            "import_details",
            "import_metadata",
            "import_reference",
            "metadata",
            "source",
            "audio_file",
        ]
        write_only_fields = ["audio_file"]
        read_only_fields = UploadSerializer.Meta.read_only_fields + [
            "import_details",
            "metadata",
        ]

    def to_representation(self, obj):
        r = super().to_representation(obj)
        if "audio_file" in r:
            del r["audio_file"]
        return r

    def validate(self, validated_data):
        if (
            not self.instance
            and "library" not in validated_data
            and "channel" not in validated_data
        ):
            raise serializers.ValidationError(
                "You need to specify a channel or a library"
            )
        if (
            not self.instance
            and "library" in validated_data
            and "channel" in validated_data
        ):
            raise serializers.ValidationError(
                "You may specify a channel or a library, not both"
            )
        if "audio_file" in validated_data:
            self.validate_upload_quota(validated_data["audio_file"])

        if "channel" in validated_data:
            validated_data["library"] = validated_data.pop("channel").library
        return super().validate(validated_data)

    def validate_upload_quota(self, f):
        quota_status = self.context["user"].get_quota_status()
        if (f.size / 1000 / 1000) > quota_status["remaining"]:
            raise serializers.ValidationError("upload_quota_reached")

        return f


class UploadActionSerializer(common_serializers.ActionSerializer):
    actions = [
        common_serializers.Action("delete", allow_all=True),
        common_serializers.Action("relaunch_import", allow_all=True),
        common_serializers.Action("publish", allow_all=False),
    ]
    filterset_class = filters.UploadFilter
    pk_field = "uuid"

    @transaction.atomic
    def handle_delete(self, objects):
        libraries = sorted(set(objects.values_list("library", flat=True)))
        for id in libraries:
            # we group deletes by library for easier federation
            uploads = objects.filter(library__pk=id).select_related("library__actor")
            for chunk in common_utils.chunk_queryset(uploads, 100):
                routes.outbox.dispatch(
                    {"type": "Delete", "object": {"type": "Audio"}},
                    context={"uploads": chunk},
                )

        return objects.delete()

    @transaction.atomic
    def handle_relaunch_import(self, objects):
        qs = objects.filter(import_status__in=["pending", "skipped", "errored"])
        pks = list(qs.values_list("id", flat=True))
        qs.update(import_status="pending")
        for pk in pks:
            common_utils.on_commit(tasks.process_upload.delay, upload_id=pk)

    @transaction.atomic
    def handle_publish(self, objects):
        qs = objects.filter(import_status="draft")
        pks = list(qs.values_list("id", flat=True))
        qs.update(import_status="pending")
        for pk in pks:
            common_utils.on_commit(tasks.process_upload.delay, upload_id=pk)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = tag_models.Tag
        fields = ("id", "name", "creation_date")


class SimpleAlbumSerializer(serializers.ModelSerializer):
    cover = cover_field

    class Meta:
        model = models.Album
        fields = ("id", "mbid", "title", "release_date", "cover")


class TrackActivitySerializer(activity_serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    name = serializers.CharField(source="title")
    artist = serializers.CharField(source="artist.name")
    album = serializers.SerializerMethodField()

    class Meta:
        model = models.Track
        fields = ["id", "local_id", "name", "type", "artist", "album"]

    def get_type(self, obj):
        return "Audio"

    def get_album(self, o):
        if o.album:
            return o.album.title


def get_embed_url(type, id):
    return settings.FUNKWHALE_EMBED_URL + "?type={}&id={}".format(type, id)


class OembedSerializer(serializers.Serializer):
    format = serializers.ChoiceField(choices=["json"])
    url = serializers.URLField()
    maxheight = serializers.IntegerField(required=False)
    maxwidth = serializers.IntegerField(required=False)

    def validate(self, validated_data):
        try:
            match = common_utils.spa_resolve(
                urllib.parse.urlparse(validated_data["url"]).path
            )
        except urls.exceptions.Resolver404:
            raise serializers.ValidationError(
                "Invalid URL {}".format(validated_data["url"])
            )
        data = {
            "version": "1.0",
            "type": "rich",
            "provider_name": settings.APP_NAME,
            "provider_url": settings.FUNKWHALE_URL,
            "height": validated_data.get("maxheight") or 400,
            "width": validated_data.get("maxwidth") or 600,
        }
        embed_id = None
        embed_type = None
        if match.url_name == "library_track":
            qs = models.Track.objects.select_related("artist", "album__artist").filter(
                pk=int(match.kwargs["pk"])
            )
            try:
                track = qs.get()
            except models.Track.DoesNotExist:
                raise serializers.ValidationError(
                    "No track matching id {}".format(match.kwargs["pk"])
                )
            embed_type = "track"
            embed_id = track.pk
            data["title"] = "{} by {}".format(track.title, track.artist.name)
            if track.attachment_cover:
                data[
                    "thumbnail_url"
                ] = track.attachment_cover.download_url_medium_square_crop
                data["thumbnail_width"] = 200
                data["thumbnail_height"] = 200
            elif track.album and track.album.attachment_cover:
                data[
                    "thumbnail_url"
                ] = track.album.attachment_cover.download_url_medium_square_crop
                data["thumbnail_width"] = 200
                data["thumbnail_height"] = 200
            data["description"] = track.full_name
            data["author_name"] = track.artist.name
            data["height"] = 150
            data["author_url"] = federation_utils.full_url(
                common_utils.spa_reverse(
                    "library_artist", kwargs={"pk": track.artist.pk}
                )
            )
        elif match.url_name == "library_album":
            qs = models.Album.objects.select_related("artist").filter(
                pk=int(match.kwargs["pk"])
            )
            try:
                album = qs.get()
            except models.Album.DoesNotExist:
                raise serializers.ValidationError(
                    "No album matching id {}".format(match.kwargs["pk"])
                )
            embed_type = "album"
            embed_id = album.pk
            if album.attachment_cover:
                data[
                    "thumbnail_url"
                ] = album.attachment_cover.download_url_medium_square_crop
                data["thumbnail_width"] = 200
                data["thumbnail_height"] = 200
            data["title"] = "{} by {}".format(album.title, album.artist.name)
            data["description"] = "{} by {}".format(album.title, album.artist.name)
            data["author_name"] = album.artist.name
            data["height"] = 400
            data["author_url"] = federation_utils.full_url(
                common_utils.spa_reverse(
                    "library_artist", kwargs={"pk": album.artist.pk}
                )
            )
        elif match.url_name == "library_artist":
            qs = models.Artist.objects.filter(pk=int(match.kwargs["pk"]))
            try:
                artist = qs.get()
            except models.Artist.DoesNotExist:
                raise serializers.ValidationError(
                    "No artist matching id {}".format(match.kwargs["pk"])
                )
            embed_type = "artist"
            embed_id = artist.pk
            album = artist.albums.exclude(attachment_cover=None).order_by("-id").first()

            if album and album.attachment_cover:
                data[
                    "thumbnail_url"
                ] = album.attachment_cover.download_url_medium_square_crop
                data["thumbnail_width"] = 200
                data["thumbnail_height"] = 200
            data["title"] = artist.name
            data["description"] = artist.name
            data["author_name"] = artist.name
            data["height"] = 400
            data["author_url"] = federation_utils.full_url(
                common_utils.spa_reverse("library_artist", kwargs={"pk": artist.pk})
            )
        elif match.url_name == "channel_detail":
            from funkwhale_api.audio.models import Channel

            kwargs = {}
            if "uuid" in match.kwargs:
                kwargs["uuid"] = match.kwargs["uuid"]
            else:
                username_data = federation_utils.get_actor_data_from_username(
                    match.kwargs["username"]
                )
                kwargs["actor__domain"] = username_data["domain"]
                kwargs["actor__preferred_username__iexact"] = username_data["username"]
            qs = Channel.objects.filter(**kwargs).select_related(
                "artist__attachment_cover"
            )
            try:
                channel = qs.get()
            except models.Artist.DoesNotExist:
                raise serializers.ValidationError(
                    "No channel matching id {}".format(match.kwargs["uuid"])
                )
            embed_type = "channel"
            embed_id = channel.uuid

            if channel.artist.attachment_cover:
                data[
                    "thumbnail_url"
                ] = channel.artist.attachment_cover.download_url_medium_square_crop
                data["thumbnail_width"] = 200
                data["thumbnail_height"] = 200
            data["title"] = channel.artist.name
            data["description"] = channel.artist.name
            data["author_name"] = channel.artist.name
            data["height"] = 400
            data["author_url"] = federation_utils.full_url(
                common_utils.spa_reverse(
                    "channel_detail", kwargs={"uuid": channel.uuid}
                )
            )
        elif match.url_name == "library_playlist":
            qs = playlists_models.Playlist.objects.filter(
                pk=int(match.kwargs["pk"]), privacy_level="everyone"
            )
            try:
                obj = qs.get()
            except playlists_models.Playlist.DoesNotExist:
                raise serializers.ValidationError(
                    "No artist matching id {}".format(match.kwargs["pk"])
                )
            embed_type = "playlist"
            embed_id = obj.pk
            playlist_tracks = obj.playlist_tracks.exclude(
                track__album__attachment_cover=None
            )
            playlist_tracks = playlist_tracks.select_related(
                "track__album__attachment_cover"
            ).order_by("index")
            first_playlist_track = playlist_tracks.first()

            if first_playlist_track:
                data[
                    "thumbnail_url"
                ] = (
                    first_playlist_track.track.album.attachment_cover.download_url_medium_square_crop
                )
                data["thumbnail_width"] = 200
                data["thumbnail_height"] = 200
            data["title"] = obj.name
            data["description"] = obj.name
            data["author_name"] = obj.name
            data["height"] = 400
            data["author_url"] = federation_utils.full_url(
                common_utils.spa_reverse("library_playlist", kwargs={"pk": obj.pk})
            )
        else:
            raise serializers.ValidationError(
                "Unsupported url: {}".format(validated_data["url"])
            )
        data[
            "html"
        ] = '<iframe width="{}" height="{}" scrolling="no" frameborder="no" src="{}"></iframe>'.format(
            data["width"], data["height"], get_embed_url(embed_type, embed_id)
        )
        return data

    def create(self, data):
        return data


class AlbumCreateSerializer(serializers.Serializer):
    title = serializers.CharField(required=True, max_length=255)
    cover = COVER_WRITE_FIELD
    release_date = serializers.DateField(required=False, allow_null=True)
    tags = tags_serializers.TagsListField(required=False)
    description = common_serializers.ContentSerializer(allow_null=True, required=False)

    artist = common_serializers.RelatedField(
        "id",
        queryset=models.Artist.objects.exclude(channel__isnull=True),
        required=True,
        serializer=None,
        filters=lambda context: {"attributed_to": context["user"].actor},
    )

    def validate(self, validated_data):
        duplicates = validated_data["artist"].albums.filter(
            title__iexact=validated_data["title"]
        )
        if duplicates.exists():
            raise serializers.ValidationError("An album with this title already exist")

        return super().validate(validated_data)

    def to_representation(self, obj):
        obj.artist.attachment_cover
        return AlbumSerializer(obj, context=self.context).data

    def create(self, validated_data):
        instance = models.Album.objects.create(
            attributed_to=self.context["user"].actor,
            artist=validated_data["artist"],
            release_date=validated_data.get("release_date"),
            title=validated_data["title"],
            attachment_cover=validated_data.get("cover"),
        )
        common_utils.attach_content(
            instance, "description", validated_data.get("description")
        )
        tag_models.set_tags(instance, *(validated_data.get("tags", []) or []))
        return instance

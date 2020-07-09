from django.conf import settings
from django.db import transaction

from rest_framework import serializers

from funkwhale_api.audio import models as audio_models
from funkwhale_api.common import fields as common_fields
from funkwhale_api.common import serializers as common_serializers
from funkwhale_api.common import utils as common_utils
from funkwhale_api.federation import models as federation_models
from funkwhale_api.federation import fields as federation_fields
from funkwhale_api.federation import tasks as federation_tasks
from funkwhale_api.moderation import models as moderation_models
from funkwhale_api.moderation import serializers as moderation_serializers
from funkwhale_api.moderation import utils as moderation_utils
from funkwhale_api.music import models as music_models
from funkwhale_api.music import serializers as music_serializers
from funkwhale_api.tags import models as tags_models
from funkwhale_api.users import models as users_models

from . import filters


class PermissionsSerializer(serializers.Serializer):
    def to_representation(self, o):
        return o.get_permissions(defaults=self.context.get("default_permissions"))

    def to_internal_value(self, o):
        return {"permissions": o}


class ManageUserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = users_models.User
        fields = (
            "id",
            "username",
            "email",
            "name",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_activity",
            "privacy_level",
            "upload_quota",
        )


class ManageUserSerializer(serializers.ModelSerializer):
    permissions = PermissionsSerializer(source="*")
    upload_quota = serializers.IntegerField(allow_null=True)
    actor = serializers.SerializerMethodField()

    class Meta:
        model = users_models.User
        fields = (
            "id",
            "username",
            "actor",
            "email",
            "name",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_activity",
            "permissions",
            "privacy_level",
            "upload_quota",
            "full_username",
        )
        read_only_fields = [
            "id",
            "email",
            "privacy_level",
            "username",
            "date_joined",
            "last_activity",
        ]

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        permissions = validated_data.pop("permissions", {})
        if permissions:
            for p, value in permissions.items():
                setattr(instance, "permission_{}".format(p), value)
            instance.save(
                update_fields=["permission_{}".format(p) for p in permissions.keys()]
            )
        return instance

    def get_actor(self, obj):
        if obj.actor:
            return ManageBaseActorSerializer(obj.actor).data


class ManageInvitationSerializer(serializers.ModelSerializer):
    users = ManageUserSimpleSerializer(many=True, required=False)
    owner = ManageUserSimpleSerializer(required=False)
    code = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = users_models.Invitation
        fields = ("id", "owner", "code", "expiration_date", "creation_date", "users")
        read_only_fields = ["id", "expiration_date", "owner", "creation_date", "users"]

    def validate_code(self, value):
        if not value:
            return value
        if users_models.Invitation.objects.filter(code__iexact=value).exists():
            raise serializers.ValidationError(
                "An invitation with this code already exists"
            )
        return value


class ManageInvitationActionSerializer(common_serializers.ActionSerializer):
    actions = [
        common_serializers.Action(
            "delete", allow_all=False, qs_filter=lambda qs: qs.open()
        )
    ]
    filterset_class = filters.ManageInvitationFilterSet

    @transaction.atomic
    def handle_delete(self, objects):
        return objects.delete()


class ManageDomainSerializer(serializers.ModelSerializer):
    actors_count = serializers.SerializerMethodField()
    outbox_activities_count = serializers.SerializerMethodField()

    class Meta:
        model = federation_models.Domain
        fields = [
            "name",
            "creation_date",
            "actors_count",
            "outbox_activities_count",
            "nodeinfo",
            "nodeinfo_fetch_date",
            "instance_policy",
            "allowed",
        ]
        read_only_fields = [
            "creation_date",
            "instance_policy",
            "nodeinfo",
            "nodeinfo_fetch_date",
        ]

    def get_actors_count(self, o):
        return getattr(o, "actors_count", 0)

    def get_outbox_activities_count(self, o):
        return getattr(o, "outbox_activities_count", 0)


class ManageDomainUpdateSerializer(ManageDomainSerializer):
    class Meta(ManageDomainSerializer.Meta):
        read_only_fields = ["name"] + ManageDomainSerializer.Meta.read_only_fields


class ManageDomainActionSerializer(common_serializers.ActionSerializer):
    actions = [
        common_serializers.Action("purge", allow_all=False),
        common_serializers.Action("allow_list_add", allow_all=True),
        common_serializers.Action("allow_list_remove", allow_all=True),
    ]
    filterset_class = filters.ManageDomainFilterSet
    pk_field = "name"

    @transaction.atomic
    def handle_purge(self, objects):
        ids = objects.values_list("pk", flat=True).order_by("pk")
        common_utils.on_commit(federation_tasks.purge_actors.delay, domains=list(ids))

    @transaction.atomic
    def handle_allow_list_add(self, objects):
        objects.update(allowed=True)

    @transaction.atomic
    def handle_allow_list_remove(self, objects):
        objects.update(allowed=False)


class ManageBaseActorSerializer(serializers.ModelSerializer):
    is_local = serializers.SerializerMethodField()

    class Meta:
        model = federation_models.Actor
        fields = [
            "id",
            "url",
            "fid",
            "preferred_username",
            "full_username",
            "domain",
            "name",
            "summary",
            "type",
            "creation_date",
            "last_fetch_date",
            "inbox_url",
            "outbox_url",
            "shared_inbox_url",
            "manually_approves_followers",
            "is_local",
        ]
        read_only_fields = ["creation_date", "instance_policy"]

    def get_is_local(self, o):
        return o.domain_id == settings.FEDERATION_HOSTNAME


class ManageActorSerializer(ManageBaseActorSerializer):
    uploads_count = serializers.SerializerMethodField()
    user = ManageUserSerializer()

    class Meta:
        model = federation_models.Actor
        fields = ManageBaseActorSerializer.Meta.fields + [
            "uploads_count",
            "user",
            "instance_policy",
        ]
        read_only_fields = ["creation_date", "instance_policy"]

    def get_uploads_count(self, o):
        return getattr(o, "uploads_count", 0)


class ManageActorActionSerializer(common_serializers.ActionSerializer):
    actions = [common_serializers.Action("purge", allow_all=False)]
    filterset_class = filters.ManageActorFilterSet

    @transaction.atomic
    def handle_purge(self, objects):
        ids = objects.values_list("id", flat=True)
        common_utils.on_commit(federation_tasks.purge_actors.delay, ids=list(ids))


class TargetSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["domain", "actor"])
    id = serializers.CharField()

    def to_representation(self, value):
        if value["type"] == "domain":
            return {"type": "domain", "id": value["obj"].name}
        if value["type"] == "actor":
            return {"type": "actor", "id": value["obj"].full_username}

    def to_internal_value(self, value):
        if value["type"] == "domain":
            field = serializers.PrimaryKeyRelatedField(
                queryset=federation_models.Domain.objects.external()
            )
        if value["type"] == "actor":
            field = federation_fields.ActorRelatedField()
        value["obj"] = field.to_internal_value(value["id"])
        return value


class ManageInstancePolicySerializer(serializers.ModelSerializer):
    target = TargetSerializer()
    actor = federation_fields.ActorRelatedField(read_only=True)

    class Meta:
        model = moderation_models.InstancePolicy
        fields = [
            "id",
            "uuid",
            "target",
            "creation_date",
            "actor",
            "summary",
            "is_active",
            "block_all",
            "silence_activity",
            "silence_notifications",
            "reject_media",
        ]

        read_only_fields = ["uuid", "id", "creation_date", "actor", "target"]

    def validate(self, data):
        try:
            target = data.pop("target")
        except KeyError:
            # partial update
            return data
        if target["type"] == "domain":
            data["target_domain"] = target["obj"]
        if target["type"] == "actor":
            data["target_actor"] = target["obj"]

        return data

    @transaction.atomic
    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        need_purge = self.instance.is_active and (
            self.instance.block_all or self.instance.reject_media
        )
        if need_purge:
            only = []
            if self.instance.reject_media:
                only.append("media")
            target = instance.target
            if target["type"] == "domain":
                common_utils.on_commit(
                    federation_tasks.purge_actors.delay,
                    domains=[target["obj"].pk],
                    only=only,
                )
            if target["type"] == "actor":
                common_utils.on_commit(
                    federation_tasks.purge_actors.delay,
                    ids=[target["obj"].pk],
                    only=only,
                )

        return instance


class ManageBaseArtistSerializer(serializers.ModelSerializer):
    domain = serializers.CharField(source="domain_name")

    class Meta:
        model = music_models.Artist
        fields = ["id", "fid", "mbid", "name", "creation_date", "domain", "is_local"]


class ManageBaseAlbumSerializer(serializers.ModelSerializer):
    cover = music_serializers.cover_field
    domain = serializers.CharField(source="domain_name")
    tracks_count = serializers.SerializerMethodField()

    class Meta:
        model = music_models.Album
        fields = [
            "id",
            "fid",
            "mbid",
            "title",
            "creation_date",
            "release_date",
            "cover",
            "domain",
            "is_local",
            "tracks_count",
        ]

    def get_tracks_count(self, o):
        return getattr(o, "_tracks_count", None)


class ManageNestedTrackSerializer(serializers.ModelSerializer):
    domain = serializers.CharField(source="domain_name")

    class Meta:
        model = music_models.Track
        fields = [
            "id",
            "fid",
            "mbid",
            "title",
            "creation_date",
            "position",
            "disc_number",
            "domain",
            "is_local",
            "copyright",
            "license",
        ]


class ManageNestedAlbumSerializer(ManageBaseAlbumSerializer):

    tracks_count = serializers.SerializerMethodField()

    class Meta:
        model = music_models.Album
        fields = ManageBaseAlbumSerializer.Meta.fields + ["tracks_count"]

    def get_tracks_count(self, obj):
        return getattr(obj, "tracks_count", None)


class ManageArtistSerializer(
    music_serializers.OptionalDescriptionMixin, ManageBaseArtistSerializer
):
    attributed_to = ManageBaseActorSerializer()
    tags = serializers.SerializerMethodField()
    tracks_count = serializers.SerializerMethodField()
    albums_count = serializers.SerializerMethodField()
    channel = serializers.SerializerMethodField()
    cover = music_serializers.cover_field

    class Meta:
        model = music_models.Artist
        fields = ManageBaseArtistSerializer.Meta.fields + [
            "tracks_count",
            "albums_count",
            "attributed_to",
            "tags",
            "cover",
            "channel",
            "content_category",
        ]

    def get_tracks_count(self, obj):
        return getattr(obj, "_tracks_count", None)

    def get_albums_count(self, obj):
        return getattr(obj, "_albums_count", None)

    def get_tags(self, obj):
        tagged_items = getattr(obj, "_prefetched_tagged_items", [])
        return [ti.tag.name for ti in tagged_items]

    def get_channel(self, obj):
        if "channel" in obj._state.fields_cache and obj.get_channel():
            return str(obj.channel.uuid)


class ManageNestedArtistSerializer(ManageBaseArtistSerializer):
    pass


class ManageAlbumSerializer(
    music_serializers.OptionalDescriptionMixin, ManageBaseAlbumSerializer
):
    attributed_to = ManageBaseActorSerializer()
    artist = ManageNestedArtistSerializer()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = music_models.Album
        fields = ManageBaseAlbumSerializer.Meta.fields + [
            "artist",
            "attributed_to",
            "tags",
            "tracks_count",
        ]

    def get_tracks_count(self, o):
        return len(o.tracks.all())

    def get_tags(self, obj):
        tagged_items = getattr(obj, "_prefetched_tagged_items", [])
        return [ti.tag.name for ti in tagged_items]


class ManageTrackAlbumSerializer(ManageBaseAlbumSerializer):
    artist = ManageNestedArtistSerializer()

    class Meta:
        model = music_models.Album
        fields = ManageBaseAlbumSerializer.Meta.fields + ["artist"]


class ManageTrackSerializer(
    music_serializers.OptionalDescriptionMixin, ManageNestedTrackSerializer
):
    artist = ManageNestedArtistSerializer()
    album = ManageTrackAlbumSerializer()
    attributed_to = ManageBaseActorSerializer()
    uploads_count = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    cover = music_serializers.cover_field

    class Meta:
        model = music_models.Track
        fields = ManageNestedTrackSerializer.Meta.fields + [
            "artist",
            "album",
            "attributed_to",
            "uploads_count",
            "tags",
            "cover",
        ]

    def get_uploads_count(self, obj):
        return getattr(obj, "uploads_count", None)

    def get_tags(self, obj):
        tagged_items = getattr(obj, "_prefetched_tagged_items", [])
        return [ti.tag.name for ti in tagged_items]


class ManageTrackActionSerializer(common_serializers.ActionSerializer):
    actions = [common_serializers.Action("delete", allow_all=False)]
    filterset_class = filters.ManageTrackFilterSet

    @transaction.atomic
    def handle_delete(self, objects):
        return objects.delete()


class ManageAlbumActionSerializer(common_serializers.ActionSerializer):
    actions = [common_serializers.Action("delete", allow_all=False)]
    filterset_class = filters.ManageAlbumFilterSet

    @transaction.atomic
    def handle_delete(self, objects):
        return objects.delete()


class ManageArtistActionSerializer(common_serializers.ActionSerializer):
    actions = [common_serializers.Action("delete", allow_all=False)]
    filterset_class = filters.ManageArtistFilterSet

    @transaction.atomic
    def handle_delete(self, objects):
        return objects.delete()


class ManageLibraryActionSerializer(common_serializers.ActionSerializer):
    actions = [common_serializers.Action("delete", allow_all=False)]
    filterset_class = filters.ManageLibraryFilterSet

    @transaction.atomic
    def handle_delete(self, objects):
        return objects.delete()


class ManageUploadActionSerializer(common_serializers.ActionSerializer):
    actions = [common_serializers.Action("delete", allow_all=False)]
    filterset_class = filters.ManageUploadFilterSet

    @transaction.atomic
    def handle_delete(self, objects):
        return objects.delete()


class ManageLibrarySerializer(serializers.ModelSerializer):
    domain = serializers.CharField(source="domain_name")
    actor = ManageBaseActorSerializer()
    uploads_count = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()

    class Meta:
        model = music_models.Library
        fields = [
            "id",
            "uuid",
            "fid",
            "url",
            "name",
            "description",
            "domain",
            "is_local",
            "creation_date",
            "privacy_level",
            "uploads_count",
            "followers_count",
            "followers_url",
            "actor",
        ]
        read_only_fields = [
            "fid",
            "uuid",
            "id",
            "url",
            "domain",
            "actor",
            "creation_date",
        ]

    def get_uploads_count(self, obj):
        return getattr(obj, "_uploads_count", obj.uploads_count)

    def get_followers_count(self, obj):
        return getattr(obj, "followers_count", None)


class ManageNestedLibrarySerializer(serializers.ModelSerializer):
    domain = serializers.CharField(source="domain_name")
    actor = ManageBaseActorSerializer()

    class Meta:
        model = music_models.Library
        fields = [
            "id",
            "uuid",
            "fid",
            "url",
            "name",
            "description",
            "domain",
            "is_local",
            "creation_date",
            "privacy_level",
            "followers_url",
            "actor",
        ]


class ManageUploadSerializer(serializers.ModelSerializer):
    track = ManageNestedTrackSerializer()
    library = ManageNestedLibrarySerializer()
    domain = serializers.CharField(source="domain_name")

    class Meta:
        model = music_models.Upload
        fields = (
            "id",
            "uuid",
            "fid",
            "domain",
            "is_local",
            "audio_file",
            "listen_url",
            "source",
            "filename",
            "mimetype",
            "duration",
            "mimetype",
            "bitrate",
            "size",
            "creation_date",
            "accessed_date",
            "modification_date",
            "metadata",
            "import_date",
            "import_details",
            "import_status",
            "import_metadata",
            "import_reference",
            "track",
            "library",
        )


class ManageTagSerializer(ManageBaseAlbumSerializer):

    tracks_count = serializers.SerializerMethodField()
    albums_count = serializers.SerializerMethodField()
    artists_count = serializers.SerializerMethodField()

    class Meta:
        model = tags_models.Tag
        fields = [
            "id",
            "name",
            "creation_date",
            "tracks_count",
            "albums_count",
            "artists_count",
        ]

    def get_tracks_count(self, obj):
        return getattr(obj, "_tracks_count", None)

    def get_albums_count(self, obj):
        return getattr(obj, "_albums_count", None)

    def get_artists_count(self, obj):
        return getattr(obj, "_artists_count", None)


class ManageTagActionSerializer(common_serializers.ActionSerializer):
    actions = [common_serializers.Action("delete", allow_all=False)]
    filterset_class = filters.ManageTagFilterSet
    pk_field = "name"

    @transaction.atomic
    def handle_delete(self, objects):
        return objects.delete()


class ManageBaseNoteSerializer(serializers.ModelSerializer):
    author = ManageBaseActorSerializer(required=False, read_only=True)

    class Meta:
        model = moderation_models.Note
        fields = ["id", "uuid", "creation_date", "summary", "author"]
        read_only_fields = ["uuid", "creation_date", "author"]


class ManageNoteSerializer(ManageBaseNoteSerializer):
    target = common_fields.GenericRelation(moderation_utils.NOTE_TARGET_FIELDS)

    class Meta(ManageBaseNoteSerializer.Meta):
        fields = ManageBaseNoteSerializer.Meta.fields + ["target"]


class ManageReportSerializer(serializers.ModelSerializer):
    assigned_to = ManageBaseActorSerializer()
    target_owner = ManageBaseActorSerializer()
    submitter = ManageBaseActorSerializer()
    target = moderation_serializers.TARGET_FIELD
    notes = serializers.SerializerMethodField()

    class Meta:
        model = moderation_models.Report
        fields = [
            "id",
            "uuid",
            "fid",
            "creation_date",
            "handled_date",
            "summary",
            "type",
            "target",
            "target_state",
            "is_handled",
            "assigned_to",
            "target_owner",
            "submitter",
            "submitter_email",
            "notes",
        ]
        read_only_fields = [
            "id",
            "uuid",
            "fid",
            "submitter",
            "submitter_email",
            "creation_date",
            "handled_date",
            "target",
            "target_state",
            "target_owner",
            "summary",
        ]

    def get_notes(self, o):
        notes = getattr(o, "_prefetched_notes", [])
        return ManageBaseNoteSerializer(notes, many=True).data


class ManageUserRequestSerializer(serializers.ModelSerializer):
    assigned_to = ManageBaseActorSerializer()
    submitter = ManageBaseActorSerializer()
    notes = serializers.SerializerMethodField()

    class Meta:
        model = moderation_models.UserRequest
        fields = [
            "id",
            "uuid",
            "creation_date",
            "handled_date",
            "type",
            "status",
            "assigned_to",
            "submitter",
            "notes",
            "metadata",
        ]
        read_only_fields = [
            "id",
            "uuid",
            "submitter",
            "creation_date",
            "handled_date",
            "metadata",
        ]

    def get_notes(self, o):
        notes = getattr(o, "_prefetched_notes", [])
        return ManageBaseNoteSerializer(notes, many=True).data


class ManageChannelSerializer(serializers.ModelSerializer):
    attributed_to = ManageBaseActorSerializer()
    actor = ManageBaseActorSerializer()
    artist = ManageArtistSerializer()

    class Meta:
        model = audio_models.Channel
        fields = [
            "id",
            "uuid",
            "creation_date",
            "artist",
            "attributed_to",
            "actor",
            "rss_url",
            "metadata",
        ]
        read_only_fields = fields

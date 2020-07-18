from django import forms
from django.db.models import Q

import django_filters
from django_filters import rest_framework as filters

from funkwhale_api.common import fields
from funkwhale_api.common import filters as common_filters
from funkwhale_api.common import search

from funkwhale_api.audio import models as audio_models
from funkwhale_api.federation import models as federation_models
from funkwhale_api.federation import utils as federation_utils
from funkwhale_api.moderation import models as moderation_models
from funkwhale_api.moderation import serializers as moderation_serializers
from funkwhale_api.moderation import utils as moderation_utils
from funkwhale_api.music import models as music_models
from funkwhale_api.users import models as users_models
from funkwhale_api.tags import models as tags_models


class ActorField(forms.CharField):
    def clean(self, value):
        value = super().clean(value)
        if not value:
            return value

        return federation_utils.get_actor_data_from_username(value)


def get_actor_filter(actor_field):
    def handler(v):
        return federation_utils.get_actor_from_username_data_query(actor_field, v)

    return {"field": ActorField(), "handler": handler}


class ManageChannelFilterSet(filters.FilterSet):
    q = fields.SmartSearchFilter(
        config=search.SearchConfig(
            search_fields={
                "name": {"to": "artist__name"},
                "username": {"to": "artist__name"},
                "fid": {"to": "artist__fid"},
                "rss": {"to": "rss_url"},
            },
            filter_fields={
                "uuid": {"to": "uuid"},
                "category": {"to": "artist__content_category"},
                "domain": {
                    "handler": lambda v: federation_utils.get_domain_query_from_url(
                        v, url_field="attributed_to__fid"
                    )
                },
                "tag": {"to": "artist__tagged_items__tag__name", "distinct": True},
                "account": get_actor_filter("attributed_to"),
            },
        )
    )

    class Meta:
        model = audio_models.Channel
        fields = []


class ManageArtistFilterSet(filters.FilterSet):
    q = fields.SmartSearchFilter(
        config=search.SearchConfig(
            search_fields={
                "name": {"to": "name"},
                "fid": {"to": "fid"},
                "mbid": {"to": "mbid"},
            },
            filter_fields={
                "uuid": {"to": "uuid"},
                "domain": {
                    "handler": lambda v: federation_utils.get_domain_query_from_url(v)
                },
                "library_id": {
                    "to": "tracks__uploads__library_id",
                    "field": forms.IntegerField(),
                    "distinct": True,
                },
                "category": {"to": "content_category"},
                "tag": {"to": "tagged_items__tag__name", "distinct": True},
            },
        )
    )

    class Meta:
        model = music_models.Artist
        fields = ["name", "mbid", "fid", "content_category"]


class ManageAlbumFilterSet(filters.FilterSet):
    q = fields.SmartSearchFilter(
        config=search.SearchConfig(
            search_fields={
                "title": {"to": "title"},
                "fid": {"to": "fid"},
                "artist": {"to": "artist__name"},
                "mbid": {"to": "mbid"},
            },
            filter_fields={
                "uuid": {"to": "uuid"},
                "artist_id": {"to": "artist_id", "field": forms.IntegerField()},
                "domain": {
                    "handler": lambda v: federation_utils.get_domain_query_from_url(v)
                },
                "library_id": {
                    "to": "tracks__uploads__library_id",
                    "field": forms.IntegerField(),
                    "distinct": True,
                },
                "tag": {"to": "tagged_items__tag__name", "distinct": True},
            },
        )
    )

    class Meta:
        model = music_models.Album
        fields = ["title", "mbid", "fid", "artist"]


class ManageTrackFilterSet(filters.FilterSet):
    q = fields.SmartSearchFilter(
        config=search.SearchConfig(
            search_fields={
                "title": {"to": "title"},
                "fid": {"to": "fid"},
                "mbid": {"to": "mbid"},
                "artist": {"to": "artist__name"},
                "album": {"to": "album__title"},
                "album_artist": {"to": "album__artist__name"},
                "copyright": {"to": "copyright"},
            },
            filter_fields={
                "album_id": {"to": "album_id", "field": forms.IntegerField()},
                "album_artist_id": {
                    "to": "album__artist_id",
                    "field": forms.IntegerField(),
                },
                "artist_id": {"to": "artist_id", "field": forms.IntegerField()},
                "uuid": {"to": "uuid"},
                "license": {"to": "license"},
                "domain": {
                    "handler": lambda v: federation_utils.get_domain_query_from_url(v)
                },
                "library_id": {
                    "to": "uploads__library_id",
                    "field": forms.IntegerField(),
                    "distinct": True,
                },
                "tag": {"to": "tagged_items__tag__name", "distinct": True},
            },
        )
    )

    class Meta:
        model = music_models.Track
        fields = ["title", "mbid", "fid", "artist", "album", "license"]


class ManageLibraryFilterSet(filters.FilterSet):
    ordering = django_filters.OrderingFilter(
        # tuple-mapping retains order
        fields=(
            ("creation_date", "creation_date"),
            ("_uploads_count", "uploads_count"),
            ("followers_count", "followers_count"),
        )
    )
    q = fields.SmartSearchFilter(
        config=search.SearchConfig(
            search_fields={
                "name": {"to": "name"},
                "description": {"to": "description"},
                "fid": {"to": "fid"},
            },
            filter_fields={
                "uuid": {"to": "uuid"},
                "artist_id": {
                    "to": "uploads__track__artist_id",
                    "field": forms.IntegerField(),
                    "distinct": True,
                },
                "album_id": {
                    "to": "uploads__track__album_id",
                    "field": forms.IntegerField(),
                    "distinct": True,
                },
                "track_id": {
                    "to": "uploads__track__id",
                    "field": forms.IntegerField(),
                    "distinct": True,
                },
                "domain": {"to": "actor__domain_id"},
                "account": get_actor_filter("actor"),
                "privacy_level": {"to": "privacy_level"},
            },
        )
    )
    domain = filters.CharFilter("actor__domain_id")

    class Meta:
        model = music_models.Library
        fields = ["name", "fid", "privacy_level"]


class ManageUploadFilterSet(filters.FilterSet):
    ordering = django_filters.OrderingFilter(
        # tuple-mapping retains order
        fields=(
            ("creation_date", "creation_date"),
            ("modification_date", "modification_date"),
            ("accessed_date", "accessed_date"),
            ("size", "size"),
            ("bitrate", "bitrate"),
            ("duration", "duration"),
        )
    )
    q = fields.SmartSearchFilter(
        config=search.SearchConfig(
            search_fields={
                "source": {"to": "source"},
                "fid": {"to": "fid"},
                "track": {"to": "track__title"},
                "album": {"to": "track__album__title"},
                "artist": {"to": "track__artist__name"},
            },
            filter_fields={
                "uuid": {"to": "uuid"},
                "library_id": {"to": "library_id", "field": forms.IntegerField()},
                "artist_id": {"to": "track__artist_id", "field": forms.IntegerField()},
                "album_id": {"to": "track__album_id", "field": forms.IntegerField()},
                "track_id": {"to": "track__id", "field": forms.IntegerField()},
                "domain": {"to": "library__actor__domain_id"},
                "import_reference": {"to": "import_reference"},
                "type": {"to": "mimetype"},
                "status": {"to": "import_status"},
                "account": get_actor_filter("library__actor"),
                "privacy_level": {"to": "library__privacy_level"},
            },
        )
    )
    domain = filters.CharFilter("library__actor__domain_id")
    privacy_level = filters.CharFilter("library__privacy_level")

    class Meta:
        model = music_models.Upload
        fields = [
            "fid",
            "mimetype",
            "import_reference",
            "import_status",
        ]


def filter_allowed(queryset, name, value):
    """
    If value=false, we want to include object with value=null as well
    """
    if value:
        return queryset.filter(allowed=True)
    else:
        return queryset.filter(Q(allowed=False) | Q(allowed__isnull=True))


class ManageDomainFilterSet(filters.FilterSet):
    q = fields.SearchFilter(search_fields=["name"])
    allowed = filters.BooleanFilter(method=filter_allowed)

    class Meta:
        model = federation_models.Domain
        fields = ["name"]


class ManageActorFilterSet(filters.FilterSet):
    q = fields.SmartSearchFilter(
        config=search.SearchConfig(
            search_fields={
                "name": {"to": "name"},
                "username": {"to": "preferred_username"},
                "email": {"to": "user__email"},
                "bio": {"to": "summary"},
                "type": {"to": "type"},
            },
            filter_fields={
                "uuid": {"to": "uuid"},
                "domain": {"to": "domain__name__iexact"},
                "username": {"to": "preferred_username__iexact"},
                "email": {"to": "user__email__iexact"},
            },
        )
    )
    local = filters.BooleanFilter(field_name="_", method="filter_local")

    class Meta:
        model = federation_models.Actor
        fields = ["domain", "type", "manually_approves_followers"]

    def filter_local(self, queryset, name, value):
        return queryset.local(value)


class ManageUserFilterSet(filters.FilterSet):
    q = fields.SmartSearchFilter(
        config=search.SearchConfig(
            search_fields={
                "name": {"to": "name"},
                "username": {"to": "username"},
                "email": {"to": "email"},
            }
        )
    )

    class Meta:
        model = users_models.User
        fields = [
            "is_active",
            "privacy_level",
            "is_staff",
            "is_superuser",
            "permission_library",
            "permission_settings",
            "permission_moderation",
        ]


class ManageInvitationFilterSet(filters.FilterSet):
    q = fields.SearchFilter(search_fields=["owner__username", "code", "owner__email"])
    is_open = filters.BooleanFilter(method="filter_is_open")

    class Meta:
        model = users_models.Invitation
        fields = []

    def filter_is_open(self, queryset, field_name, value):
        if value is None:
            return queryset
        return queryset.open(value)


class ManageInstancePolicyFilterSet(filters.FilterSet):
    q = fields.SearchFilter(
        search_fields=[
            "summary",
            "target_domain__name",
            "target_actor__username",
            "target_actor__domain__name",
        ]
    )

    target_domain = filters.CharFilter("target_domain__name")
    target_account_domain = filters.CharFilter("target_actor__domain__name")
    target_account_username = filters.CharFilter("target_actor__preferred_username")

    class Meta:
        model = moderation_models.InstancePolicy
        fields = [
            "block_all",
            "silence_activity",
            "silence_notifications",
            "reject_media",
        ]


class ManageTagFilterSet(filters.FilterSet):
    q = fields.SearchFilter(search_fields=["name"])

    class Meta:
        model = tags_models.Tag
        fields = []


class ManageReportFilterSet(filters.FilterSet):
    q = fields.SmartSearchFilter(
        config=search.SearchConfig(
            search_fields={"summary": {"to": "summary"}},
            filter_fields={
                "uuid": {"to": "uuid"},
                "id": {"to": "id"},
                "resolved": common_filters.get_boolean_filter("is_handled"),
                "domain": {"to": "target_owner__domain_id"},
                "category": {"to": "type"},
                "submitter": get_actor_filter("submitter"),
                "assigned_to": get_actor_filter("assigned_to"),
                "target_owner": get_actor_filter("target_owner"),
                "submitter_email": {"to": "submitter_email"},
                "target": common_filters.get_generic_relation_filter(
                    "target", moderation_serializers.TARGET_CONFIG
                ),
            },
        )
    )

    class Meta:
        model = moderation_models.Report
        fields = ["is_handled", "type", "submitter_email"]


class ManageNoteFilterSet(filters.FilterSet):
    q = fields.SmartSearchFilter(
        config=search.SearchConfig(
            search_fields={"summary": {"to": "summary"}},
            filter_fields={
                "uuid": {"to": "uuid"},
                "author": get_actor_filter("author"),
                "target": common_filters.get_generic_relation_filter(
                    "target", moderation_utils.NOTE_TARGET_FIELDS
                ),
            },
        )
    )

    class Meta:
        model = moderation_models.Note
        fields = []


class ManageUserRequestFilterSet(filters.FilterSet):
    q = fields.SmartSearchFilter(
        config=search.SearchConfig(
            search_fields={
                "username": {"to": "submitter__preferred_username"},
                "uuid": {"to": "uuid"},
            },
            filter_fields={
                "uuid": {"to": "uuid"},
                "id": {"to": "id"},
                "status": {"to": "status"},
                "category": {"to": "type"},
                "submitter": get_actor_filter("submitter"),
                "assigned_to": get_actor_filter("assigned_to"),
            },
        )
    )

    class Meta:
        model = moderation_models.UserRequest
        fields = ["status", "type"]

import django_filters.widgets

from funkwhale_api.common import fields

from . import models


class FollowFilter(django_filters.FilterSet):
    pending = django_filters.CharFilter(method="filter_pending")
    ordering = django_filters.OrderingFilter(
        # tuple-mapping retains order
        fields=(
            ("creation_date", "creation_date"),
            ("modification_date", "modification_date"),
        )
    )
    q = fields.SearchFilter(
        search_fields=["actor__domain", "actor__preferred_username"]
    )

    class Meta:
        model = models.Follow
        fields = ["approved"]

    def filter_pending(self, queryset, field_name, value):
        if value.lower() in ["true", "1", "yes"]:
            queryset = queryset.filter(approved__isnull=True)
        return queryset


class LibraryFollowFilter(django_filters.FilterSet):
    class Meta:
        model = models.LibraryFollow
        fields = ["approved"]


class InboxItemFilter(django_filters.FilterSet):
    is_read = django_filters.BooleanFilter(
        "is_read", widget=django_filters.widgets.BooleanWidget()
    )
    before = django_filters.NumberFilter(method="filter_before")

    class Meta:
        model = models.InboxItem
        fields = ["is_read", "activity__type", "activity__actor"]

    def filter_before(self, queryset, field_name, value):
        return queryset.filter(pk__lte=value)


class FetchFilter(django_filters.FilterSet):
    ordering = django_filters.OrderingFilter(
        # tuple-mapping retains order
        fields=(("creation_date", "creation_date"), ("fetch_date", "fetch_date"))
    )

    class Meta:
        model = models.Fetch
        fields = ["status", "object_id", "url"]

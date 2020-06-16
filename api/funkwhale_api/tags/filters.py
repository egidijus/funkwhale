import django_filters
from django_filters import rest_framework as filters

from funkwhale_api.common import fields

from . import models


class TagFilter(filters.FilterSet):
    q = fields.SearchFilter(search_fields=["name"])
    ordering = django_filters.OrderingFilter(
        fields=(
            ("name", "name"),
            ("creation_date", "creation_date"),
            ("__size", "length"),
        )
    )

    class Meta:
        model = models.Tag
        fields = {"name": ["exact", "startswith"]}

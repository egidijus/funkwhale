from django.db import models as dj_models

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
        fields = {"q": ["exact"], "name": ["exact", "startswith"]}


def get_by_similar_tags(qs, tags):
    """
    Return a queryset of obects with at least one matching tag.
    Annotate the queryset so you can order later by number of matches.
    """
    qs = qs.filter(tagged_items__tag__name__in=tags).annotate(
        tag_matches=dj_models.Count(
            dj_models.Case(
                dj_models.When(tagged_items__tag__name__in=tags, then=1),
                output_field=dj_models.IntegerField(),
            )
        )
    )
    return qs.distinct()

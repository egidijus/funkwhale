import django_filters

from django_filters import rest_framework as filters

from funkwhale_api.common import filters as common_filters
from funkwhale_api.music import utils

from . import models


class RadioFilter(django_filters.FilterSet):
    scope = common_filters.ActorScopeFilter(actor_field="user__actor", distinct=True)
    q = filters.CharFilter(field_name="_", method="filter_q")

    class Meta:
        model = models.Radio
        fields = {
            "name": ["exact", "iexact", "startswith", "icontains"],
        }

    def filter_q(self, queryset, name, value):
        query = utils.get_query(value, ["name", "user__username"])
        return queryset.filter(query)

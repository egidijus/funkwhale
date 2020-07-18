import django_filters

from funkwhale_api.common import filters as common_filters
from . import models


class RadioFilter(django_filters.FilterSet):
    scope = common_filters.ActorScopeFilter(actor_field="user__actor", distinct=True)

    class Meta:
        model = models.Radio
        fields = {
            "name": ["exact", "iexact", "startswith", "icontains"],
        }

from funkwhale_api.common import fields
from funkwhale_api.common import filters as common_filters
from funkwhale_api.moderation import filters as moderation_filters

from . import models


class TrackFavoriteFilter(moderation_filters.HiddenContentFilterSet):
    q = fields.SearchFilter(
        search_fields=["track__title", "track__artist__name", "track__album__title"]
    )
    scope = common_filters.ActorScopeFilter(actor_field="user__actor", distinct=True)

    class Meta:
        model = models.TrackFavorite
        fields = []
        hidden_content_fields_mapping = moderation_filters.USER_FILTER_CONFIG[
            "TRACK_FAVORITE"
        ]

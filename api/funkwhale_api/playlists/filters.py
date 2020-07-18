from django.db.models import Count
from django_filters import rest_framework as filters

from funkwhale_api.common import filters as common_filters
from funkwhale_api.music import models as music_models
from funkwhale_api.music import utils

from . import models


class PlaylistFilter(filters.FilterSet):
    q = filters.CharFilter(field_name="_", method="filter_q")
    playable = filters.BooleanFilter(field_name="_", method="filter_playable")
    track = filters.ModelChoiceFilter(
        "playlist_tracks__track",
        queryset=music_models.Track.objects.all(),
        distinct=True,
    )
    album = filters.ModelChoiceFilter(
        "playlist_tracks__track__album",
        queryset=music_models.Album.objects.all(),
        distinct=True,
    )
    artist = filters.ModelChoiceFilter(
        "playlist_tracks__track__artist",
        queryset=music_models.Artist.objects.all(),
        distinct=True,
    )
    scope = common_filters.ActorScopeFilter(actor_field="user__actor", distinct=True)

    class Meta:
        model = models.Playlist
        fields = {
            "user": ["exact"],
            "name": ["exact", "icontains"],
        }

    def filter_playable(self, queryset, name, value):
        queryset = queryset.annotate(plts_count=Count("playlist_tracks"))
        if value:
            return queryset.filter(plts_count__gt=0)
        else:
            return queryset.filter(plts_count=0)

    def filter_q(self, queryset, name, value):
        query = utils.get_query(value, ["name", "user__username"])
        return queryset.filter(query)

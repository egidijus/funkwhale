from rest_framework import serializers

from funkwhale_api.federation import serializers as federation_serializers
from funkwhale_api.music.models import Track
from funkwhale_api.music.serializers import TrackSerializer
from funkwhale_api.users.serializers import UserBasicSerializer

from . import models


class PlaylistTrackSerializer(serializers.ModelSerializer):
    # track = TrackSerializer()
    track = serializers.SerializerMethodField()

    class Meta:
        model = models.PlaylistTrack
        fields = ("track", "index", "creation_date")

    def get_track(self, o):
        track = o._prefetched_track if hasattr(o, "_prefetched_track") else o.track
        return TrackSerializer(track).data


class PlaylistSerializer(serializers.ModelSerializer):
    tracks_count = serializers.SerializerMethodField(read_only=True)
    duration = serializers.SerializerMethodField(read_only=True)
    album_covers = serializers.SerializerMethodField(read_only=True)
    user = UserBasicSerializer(read_only=True)
    is_playable = serializers.SerializerMethodField()
    actor = serializers.SerializerMethodField()

    class Meta:
        model = models.Playlist
        fields = (
            "id",
            "name",
            "user",
            "modification_date",
            "creation_date",
            "privacy_level",
            "tracks_count",
            "album_covers",
            "duration",
            "is_playable",
            "actor",
        )
        read_only_fields = ["id", "modification_date", "creation_date"]

    def get_actor(self, obj):
        actor = obj.user.actor
        if actor:
            return federation_serializers.APIActorSerializer(actor).data

    def get_is_playable(self, obj):
        try:
            return bool(obj.playable_plts)
        except AttributeError:
            return None

    def get_tracks_count(self, obj):
        try:
            return obj.tracks_count
        except AttributeError:
            # no annotation?
            return obj.playlist_tracks.count()

    def get_duration(self, obj):
        try:
            return obj.duration
        except AttributeError:
            # no annotation?
            return 0

    def get_album_covers(self, obj):
        try:
            plts = obj.plts_for_cover
        except AttributeError:
            return []

        excluded_artists = []
        try:
            user = self.context["request"].user
        except (KeyError, AttributeError):
            user = None
        if user and user.is_authenticated:
            excluded_artists = list(
                user.content_filters.values_list("target_artist", flat=True)
            )

        covers = []
        max_covers = 5
        for plt in plts:
            if plt.track.album.artist_id in excluded_artists:
                continue
            url = plt.track.album.attachment_cover.download_url_medium_square_crop
            if url in covers:
                continue
            covers.append(url)
            if len(covers) >= max_covers:
                break

        full_urls = []
        for url in covers:
            if "request" in self.context:
                url = self.context["request"].build_absolute_uri(url)
            full_urls.append(url)
        return full_urls


class PlaylistAddManySerializer(serializers.Serializer):
    tracks = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Track.objects.for_nested_serialization()
    )
    allow_duplicates = serializers.BooleanField(required=False)

    class Meta:
        fields = "allow_duplicates"

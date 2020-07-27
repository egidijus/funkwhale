from django.db import models, transaction
from django.utils import timezone
from rest_framework import exceptions

from funkwhale_api.common import fields, preferences
from funkwhale_api.music import models as music_models


class PlaylistQuerySet(models.QuerySet):
    def with_tracks_count(self):
        return self.annotate(_tracks_count=models.Count("playlist_tracks"))

    def with_duration(self):
        return self.annotate(
            duration=models.Sum("playlist_tracks__track__uploads__duration")
        )

    def with_covers(self):
        album_prefetch = models.Prefetch(
            "album",
            queryset=music_models.Album.objects.select_related("attachment_cover"),
        )
        track_prefetch = models.Prefetch(
            "track",
            queryset=music_models.Track.objects.prefetch_related(album_prefetch).only(
                "id", "album_id"
            ),
        )

        plt_prefetch = models.Prefetch(
            "playlist_tracks",
            queryset=PlaylistTrack.objects.all()
            .exclude(track__album__attachment_cover=None)
            .order_by("index")
            .only("id", "playlist_id", "track_id")
            .prefetch_related(track_prefetch),
            to_attr="plts_for_cover",
        )
        return self.prefetch_related(plt_prefetch)

    def with_playable_plts(self, actor):
        return self.prefetch_related(
            models.Prefetch(
                "playlist_tracks",
                queryset=PlaylistTrack.objects.playable_by(actor),
                to_attr="playable_plts",
            )
        )

    def playable_by(self, actor, include=True):
        plts = PlaylistTrack.objects.playable_by(actor, include)
        if include:
            return self.filter(playlist_tracks__in=plts).distinct()
        else:
            return self.exclude(playlist_tracks__in=plts).distinct()


class Playlist(models.Model):
    name = models.CharField(max_length=50)
    user = models.ForeignKey(
        "users.User", related_name="playlists", on_delete=models.CASCADE
    )
    creation_date = models.DateTimeField(default=timezone.now)
    modification_date = models.DateTimeField(auto_now=True)
    privacy_level = fields.get_privacy_field()

    objects = PlaylistQuerySet.as_manager()

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return "/library/playlists/{}".format(self.pk)

    @transaction.atomic
    def insert(self, plt, index=None, allow_duplicates=True):
        """
        Given a PlaylistTrack, insert it at the correct index in the playlist,
        and update other tracks index if necessary.
        """
        old_index = plt.index
        move = old_index is not None
        if index is not None and index == old_index:
            # moving at same position, just skip
            return index

        existing = self.playlist_tracks.select_for_update()
        if move:
            existing = existing.exclude(pk=plt.pk)
        total = existing.filter(index__isnull=False).count()

        if index is None:
            # we simply increment the last track index by 1
            index = total

        if index > total:
            raise exceptions.ValidationError("Index is not continuous")

        if index < 0:
            raise exceptions.ValidationError("Index must be zero or positive")

        if not allow_duplicates:
            existing_without_current_plt = existing.exclude(pk=plt.pk)
            self._check_duplicate_add(existing_without_current_plt, [plt.track])

        if move:
            # we remove the index temporarily, to avoid integrity errors
            plt.index = None
            plt.save(update_fields=["index"])
            if index > old_index:
                # new index is higher than current, we decrement previous tracks
                to_update = existing.filter(index__gt=old_index, index__lte=index)
                to_update.update(index=models.F("index") - 1)
            if index < old_index:
                # new index is lower than current, we increment next tracks
                to_update = existing.filter(index__lt=old_index, index__gte=index)
                to_update.update(index=models.F("index") + 1)
        else:
            to_update = existing.filter(index__gte=index)
            to_update.update(index=models.F("index") + 1)

        plt.index = index
        plt.save(update_fields=["index"])
        self.save(update_fields=["modification_date"])
        return index

    @transaction.atomic
    def remove(self, index):
        existing = self.playlist_tracks.select_for_update()
        self.save(update_fields=["modification_date"])
        to_update = existing.filter(index__gt=index)
        return to_update.update(index=models.F("index") - 1)

    @transaction.atomic
    def insert_many(self, tracks, allow_duplicates=True):
        existing = self.playlist_tracks.select_for_update()
        now = timezone.now()
        total = existing.filter(index__isnull=False).count()
        max_tracks = preferences.get("playlists__max_tracks")
        if existing.count() + len(tracks) > max_tracks:
            raise exceptions.ValidationError(
                "Playlist would reach the maximum of {} tracks".format(max_tracks)
            )

        if not allow_duplicates:
            self._check_duplicate_add(existing, tracks)

        self.save(update_fields=["modification_date"])
        start = total
        plts = [
            PlaylistTrack(
                creation_date=now, playlist=self, track=track, index=start + i
            )
            for i, track in enumerate(tracks)
        ]
        return PlaylistTrack.objects.bulk_create(plts)

    def _check_duplicate_add(self, existing_playlist_tracks, tracks_to_add):
        track_ids = [t.pk for t in tracks_to_add]

        duplicates = existing_playlist_tracks.filter(
            track__pk__in=track_ids
        ).values_list("track__pk", flat=True)
        if duplicates:
            duplicate_tracks = [t for t in tracks_to_add if t.pk in duplicates]
            raise exceptions.ValidationError(
                {
                    "non_field_errors": [
                        {
                            "tracks": duplicate_tracks,
                            "playlist_name": self.name,
                            "code": "tracks_already_exist_in_playlist",
                        }
                    ]
                }
            )


class PlaylistTrackQuerySet(models.QuerySet):
    def for_nested_serialization(self, actor=None):
        tracks = music_models.Track.objects.with_playable_uploads(actor)
        tracks = tracks.select_related(
            "artist", "album__artist", "album__attachment_cover", "attributed_to"
        )
        return self.prefetch_related(
            models.Prefetch("track", queryset=tracks, to_attr="_prefetched_track")
        )

    def annotate_playable_by_actor(self, actor):
        tracks = (
            music_models.Upload.objects.playable_by(actor)
            .filter(track__pk=models.OuterRef("track"))
            .order_by("id")
            .values("id")[:1]
        )
        subquery = models.Subquery(tracks)
        return self.annotate(is_playable_by_actor=subquery)

    def playable_by(self, actor, include=True):
        tracks = music_models.Track.objects.playable_by(actor, include)
        if include:
            return self.filter(track__pk__in=tracks).distinct()
        else:
            return self.exclude(track__pk__in=tracks).distinct()

    def by_index(self, index):
        plts = self.order_by("index").values_list("id", flat=True)
        try:
            plt_id = plts[index]
        except IndexError:
            raise PlaylistTrack.DoesNotExist

        return PlaylistTrack.objects.get(pk=plt_id)


class PlaylistTrack(models.Model):
    track = models.ForeignKey(
        "music.Track", related_name="playlist_tracks", on_delete=models.CASCADE
    )
    index = models.PositiveIntegerField(null=True, blank=True)
    playlist = models.ForeignKey(
        Playlist, related_name="playlist_tracks", on_delete=models.CASCADE
    )
    creation_date = models.DateTimeField(default=timezone.now)

    objects = PlaylistTrackQuerySet.as_manager()

    class Meta:
        ordering = ("-playlist", "index")
        unique_together = ("playlist", "index")

    def delete(self, *args, **kwargs):
        playlist = self.playlist
        index = self.index
        update_indexes = kwargs.pop("update_indexes", False)
        r = super().delete(*args, **kwargs)
        if index is not None and update_indexes:
            playlist.remove(index)
        return r

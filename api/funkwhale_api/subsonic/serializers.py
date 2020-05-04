import collections

from django.db.models import Count, functions
from rest_framework import serializers

from funkwhale_api.history import models as history_models
from funkwhale_api.music import models as music_models
from funkwhale_api.music import utils as music_utils


def to_subsonic_date(date):
    """
    Subsonic expects this kind of date format: 2012-04-17T19:55:49.000Z
    """

    if not date:
        return

    return date.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def get_valid_filepart(s):
    """
    Return a string suitable for use in a file path. Escape most non-ASCII
    chars, and truncate the string to a suitable length too.
    """
    max_length = 50
    keepcharacters = " ._()[]-+"
    final = "".join(
        c if c.isalnum() or c in keepcharacters else "_" for c in s
    ).rstrip()
    return final[:max_length]


def get_track_path(track, suffix):
    parts = []
    parts.append(get_valid_filepart(track.artist.name))
    if track.album:
        parts.append(get_valid_filepart(track.album.title))
    track_part = get_valid_filepart(track.title) + "." + suffix
    if track.position:
        track_part = "{} - {}".format(track.position, track_part)
    parts.append(track_part)
    return "/".join(parts)


def get_artist_data(artist_values):
    return {
        "id": artist_values["id"],
        "name": artist_values["name"],
        "albumCount": artist_values["_albums_count"],
    }


class GetArtistsSerializer(serializers.Serializer):
    def to_representation(self, queryset):
        payload = {"ignoredArticles": "", "index": []}
        queryset = queryset.with_albums_count()
        queryset = queryset.order_by(functions.Lower("name"))
        values = queryset.values("id", "_albums_count", "name")

        first_letter_mapping = collections.defaultdict(list)
        for artist in values:
            if artist["name"]:
                first_letter_mapping[artist["name"][0].upper()].append(artist)

        for letter, artists in sorted(first_letter_mapping.items()):
            letter_data = {
                "name": letter,
                "artist": [get_artist_data(v) for v in artists],
            }
            payload["index"].append(letter_data)
        return payload


class GetArtistSerializer(serializers.Serializer):
    def to_representation(self, artist):
        albums = artist.albums.prefetch_related("tracks__uploads")
        payload = {
            "id": artist.pk,
            "name": artist.name,
            "albumCount": len(albums),
            "album": [],
        }
        for album in albums:
            album_data = {
                "id": album.id,
                "artistId": artist.id,
                "name": album.title,
                "artist": artist.name,
                "created": to_subsonic_date(album.creation_date),
                "songCount": len(album.tracks.all()),
            }
            if album.attachment_cover_id:
                album_data["coverArt"] = "al-{}".format(album.id)
            if album.release_date:
                album_data["year"] = album.release_date.year
            payload["album"].append(album_data)
        return payload


def get_track_data(album, track, upload):
    data = {
        "id": track.pk,
        "isDir": "false",
        "title": track.title,
        "album": album.title if album else "",
        "artist": track.artist.name,
        "track": track.position or 1,
        "discNumber": track.disc_number or 1,
        # Ugly fallback to mp3 but some subsonic clients fail if the value is empty or null, and we don't always
        # have the info on legacy uploads
        "contentType": upload.mimetype
        or (
            music_utils.get_type_from_ext(upload.extension)
            if upload.extension
            else "audio/mpeg"
        ),
        "suffix": upload.extension or "",
        "path": get_track_path(track, upload.extension or "mp3"),
        "duration": upload.duration or 0,
        "created": to_subsonic_date(track.creation_date),
        "albumId": album.pk if album else "",
        "artistId": album.artist.pk if album else track.artist.pk,
        "type": "music",
    }
    if album and album.attachment_cover_id:
        data["coverArt"] = "al-{}".format(album.id)
    if upload.bitrate:
        data["bitrate"] = int(upload.bitrate / 1000)
    if upload.size:
        data["size"] = upload.size
    if album and album.release_date:
        data["year"] = album.release_date.year
    else:
        data["year"] = track.creation_date.year
    return data


def get_album2_data(album):
    payload = {
        "id": album.id,
        "artistId": album.artist.id,
        "name": album.title,
        "artist": album.artist.name,
        "created": to_subsonic_date(album.creation_date),
    }
    if album.attachment_cover_id:
        payload["coverArt"] = "al-{}".format(album.id)

    try:
        payload["songCount"] = album._tracks_count
    except AttributeError:
        payload["songCount"] = len(album.tracks.prefetch_related("uploads"))
    return payload


def get_song_list_data(tracks):
    songs = []
    for track in tracks:
        try:
            uploads = [upload for upload in track.uploads.all()][0]
        except IndexError:
            continue
        track_data = get_track_data(track.album, track, uploads)
        songs.append(track_data)
    return songs


class GetAlbumSerializer(serializers.Serializer):
    def to_representation(self, album):
        tracks = album.tracks.prefetch_related("uploads").select_related("album")
        payload = get_album2_data(album)
        if album.release_date:
            payload["year"] = album.release_date.year

        payload["song"] = get_song_list_data(tracks)
        return payload


class GetSongSerializer(serializers.Serializer):
    def to_representation(self, track):
        uploads = track.uploads.all()
        if not len(uploads):
            return {}
        return get_track_data(track.album, track, uploads[0])


def get_starred_tracks_data(favorites):
    by_track_id = {f.track_id: f for f in favorites}
    tracks = (
        music_models.Track.objects.filter(pk__in=by_track_id.keys())
        .select_related("album__artist")
        .prefetch_related("uploads")
    )
    tracks = tracks.order_by("-creation_date")
    data = []
    for t in tracks:
        try:
            uploads = [upload for upload in t.uploads.all()][0]
        except IndexError:
            continue
        td = get_track_data(t.album, t, uploads)
        td["starred"] = to_subsonic_date(by_track_id[t.pk].creation_date)
        data.append(td)
    return data


def get_album_list2_data(albums):
    return [get_album2_data(a) for a in albums]


def get_playlist_data(playlist):
    return {
        "id": playlist.pk,
        "name": playlist.name,
        "owner": playlist.user.username,
        "public": "false",
        "songCount": playlist._tracks_count,
        "duration": 0,
        "created": to_subsonic_date(playlist.creation_date),
    }


def get_playlist_detail_data(playlist):
    data = get_playlist_data(playlist)
    qs = (
        playlist.playlist_tracks.select_related("track__album__artist")
        .prefetch_related("track__uploads")
        .order_by("index")
    )
    data["entry"] = []
    for plt in qs:
        try:
            uploads = [upload for upload in plt.track.uploads.all()][0]
        except IndexError:
            continue
        td = get_track_data(plt.track.album, plt.track, uploads)
        data["entry"].append(td)
    return data


def get_folders(user):
    return [
        # Dummy folder ID to match what is returned in the getMusicFolders endpoint
        # cf https://dev.funkwhale.audio/funkwhale/funkwhale/issues/624
        {"id": 1, "name": "Music"}
    ]


def get_user_detail_data(user):
    return {
        "username": user.username,
        "email": user.email,
        "scrobblingEnabled": "true",
        "adminRole": "false",
        "settingsRole": "false",
        "commentRole": "false",
        "podcastRole": "true",
        "coverArtRole": "false",
        "shareRole": "false",
        "uploadRole": "true",
        "downloadRole": "true",
        "playlistRole": "true",
        "streamRole": "true",
        "jukeboxRole": "true",
        "folder": [{"value": f["id"]} for f in get_folders(user)],
    }


class ScrobbleSerializer(serializers.Serializer):
    submission = serializers.BooleanField(default=True, required=False)
    id = serializers.PrimaryKeyRelatedField(
        queryset=music_models.Track.objects.annotate(
            uploads_count=Count("uploads")
        ).filter(uploads_count__gt=0)
    )

    def create(self, data):
        return history_models.Listening.objects.create(
            user=self.context["user"], track=data["id"]
        )


def get_genre_data(tag):
    return {
        "songCount": getattr(tag, "_tracks_count", 0),
        "albumCount": getattr(tag, "_albums_count", 0),
        "value": tag.name,
    }


def get_channel_data(channel, uploads):
    data = {
        "id": str(channel.uuid),
        "url": channel.get_rss_url(),
        "title": channel.artist.name,
        "description": channel.artist.description.as_plain_text
        if channel.artist.description
        else "",
        "coverArt": "at-{}".format(channel.artist.attachment_cover.uuid)
        if channel.artist.attachment_cover
        else "",
        "originalImageUrl": channel.artist.attachment_cover.url
        if channel.artist.attachment_cover
        else "",
        "status": "completed",
    }
    if uploads:
        data["episode"] = [
            get_channel_episode_data(upload, channel.uuid) for upload in uploads
        ]

    return data


def get_channel_episode_data(upload, channel_id):
    return {
        "id": str(upload.uuid),
        "channelId": str(channel_id),
        "streamId": upload.track.id,
        "title": upload.track.title,
        "description": upload.track.description.as_plain_text
        if upload.track.description
        else "",
        "coverArt": "at-{}".format(upload.track.attachment_cover.uuid)
        if upload.track.attachment_cover
        else "",
        "isDir": "false",
        "year": upload.track.creation_date.year,
        "publishDate": upload.track.creation_date.isoformat(),
        "created": upload.track.creation_date.isoformat(),
        "genre": "Podcast",
        "size": upload.size if upload.size else "",
        "duration": upload.duration if upload.duration else "",
        "bitrate": upload.bitrate / 1000 if upload.bitrate else "",
        "contentType": upload.mimetype or "audio/mpeg",
        "suffix": upload.extension or "mp3",
        "status": "completed",
    }

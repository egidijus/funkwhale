import datetime
import json

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.response import Response

import funkwhale_api
from funkwhale_api.moderation import filters as moderation_filters
from funkwhale_api.music import models as music_models
from funkwhale_api.music import views as music_views
from funkwhale_api.subsonic import renderers, serializers


def render_json(data):
    return json.loads(renderers.SubsonicJSONRenderer().render(data))


def test_render_content_json(db, api_client):
    url = reverse("api:subsonic-ping")
    response = api_client.get(url, {"f": "json"})

    expected = {
        "status": "ok",
        "version": "1.16.0",
        "type": "funkwhale",
        "funkwhaleVersion": funkwhale_api.__version__,
    }
    assert response.status_code == 200
    assert json.loads(response.content) == render_json(expected)


@pytest.mark.parametrize("f", ["xml", "json"])
def test_exception_wrong_credentials(f, db, api_client):
    url = reverse("api:subsonic-ping")
    response = api_client.get(url, {"f": f, "u": "yolo"})

    expected = {
        "status": "failed",
        "error": {"code": 40, "message": "Wrong username or password."},
    }
    assert response.status_code == 200
    assert response.data == expected


@pytest.mark.parametrize("f", ["json"])
def test_exception_missing_credentials(f, db, api_client):
    url = reverse("api:subsonic-get_artists")
    response = api_client.get(url)

    expected = {
        "status": "failed",
        "error": {"code": 10, "message": "Required parameter is missing."},
    }

    assert response.status_code == 200
    assert response.data == expected


def test_disabled_subsonic(preferences, api_client):
    preferences["subsonic__enabled"] = False
    url = reverse("api:subsonic-ping")
    response = api_client.get(url)
    assert response.status_code == 405


@pytest.mark.parametrize("f", ["xml", "json"])
def test_get_license(f, db, logged_in_api_client, mocker):
    url = reverse("api:subsonic-get_license")
    assert url.endswith("getLicense") is True
    now = timezone.now()
    mocker.patch("django.utils.timezone.now", return_value=now)
    response = logged_in_api_client.get(url, {"f": f})
    expected = {
        "status": "ok",
        "version": "1.16.0",
        "type": "funkwhale",
        "funkwhaleVersion": funkwhale_api.__version__,
        "license": {
            "valid": "true",
            "email": "valid@valid.license",
            "licenseExpires": now + datetime.timedelta(days=365),
        },
    }
    assert response.status_code == 200
    assert response.data == expected


@pytest.mark.parametrize("f", ["xml", "json"])
def test_ping(f, db, api_client):
    url = reverse("api:subsonic-ping")
    response = api_client.get(url, {"f": f})

    expected = {"status": "ok", "version": "1.16.0"}
    assert response.status_code == 200
    assert response.data == expected


@pytest.mark.parametrize("f", ["json"])
def test_get_artists(
    f, db, logged_in_api_client, factories, mocker, queryset_equal_queries
):
    factories["moderation.UserFilter"](
        user=logged_in_api_client.user,
        target_artist=factories["music.Artist"](playable=True),
    )
    url = reverse("api:subsonic-get_artists")
    assert url.endswith("getArtists") is True
    factories["music.Artist"].create_batch(size=3, playable=True)
    playable_by = mocker.spy(music_models.ArtistQuerySet, "playable_by")
    exclude_query = moderation_filters.get_filtered_content_query(
        moderation_filters.USER_FILTER_CONFIG["ARTIST"], logged_in_api_client.user
    )
    assert exclude_query is not None
    expected = {
        "artists": serializers.GetArtistsSerializer(
            music_models.Artist.objects.all().exclude(exclude_query)
        ).data
    }
    response = logged_in_api_client.get(url, {"f": f})

    assert response.status_code == 200
    assert response.data == expected
    playable_by.assert_called_once_with(
        music_models.Artist.objects.all().exclude(exclude_query),
        logged_in_api_client.user.actor,
    )


@pytest.mark.parametrize("f", ["json"])
def test_get_artist(
    f, db, logged_in_api_client, factories, mocker, queryset_equal_queries
):
    url = reverse("api:subsonic-get_artist")
    assert url.endswith("getArtist") is True
    artist = factories["music.Artist"](playable=True)
    factories["music.Album"].create_batch(size=3, artist=artist, playable=True)
    playable_by = mocker.spy(music_models.ArtistQuerySet, "playable_by")

    expected = {"artist": serializers.GetArtistSerializer(artist).data}
    response = logged_in_api_client.get(url, {"id": artist.pk})

    assert response.status_code == 200
    assert response.data == expected
    playable_by.assert_called_once_with(music_models.Artist.objects.all(), None)


@pytest.mark.parametrize("f", ["json"])
def test_get_invalid_artist(f, db, logged_in_api_client, factories):
    url = reverse("api:subsonic-get_artist")
    assert url.endswith("getArtist") is True
    expected = {"error": {"code": 0, "message": 'For input string "asdf"'}}
    response = logged_in_api_client.get(url, {"id": "asdf"})

    assert response.status_code == 200
    assert response.data == expected


@pytest.mark.parametrize("f", ["json"])
def test_get_artist_info2(
    f, db, logged_in_api_client, factories, mocker, queryset_equal_queries
):
    url = reverse("api:subsonic-get_artist_info2")
    assert url.endswith("getArtistInfo2") is True
    artist = factories["music.Artist"](playable=True)
    playable_by = mocker.spy(music_models.ArtistQuerySet, "playable_by")

    expected = {"artist-info2": {}}
    response = logged_in_api_client.get(url, {"id": artist.pk})

    assert response.status_code == 200
    assert response.data == expected

    playable_by.assert_called_once_with(music_models.Artist.objects.all(), None)


@pytest.mark.parametrize("f", ["json"])
def test_get_album(
    f, db, logged_in_api_client, factories, mocker, queryset_equal_queries
):
    url = reverse("api:subsonic-get_album")
    assert url.endswith("getAlbum") is True
    artist = factories["music.Artist"]()
    album = factories["music.Album"](artist=artist)
    factories["music.Track"].create_batch(size=3, album=album, playable=True)
    playable_by = mocker.spy(music_models.AlbumQuerySet, "playable_by")
    expected = {"album": serializers.GetAlbumSerializer(album).data}
    response = logged_in_api_client.get(url, {"f": f, "id": album.pk})

    assert response.status_code == 200
    assert response.data == expected

    playable_by.assert_called_once_with(
        music_models.Album.objects.select_related("artist"), None
    )


@pytest.mark.parametrize("f", ["json"])
def test_get_song(
    f, db, logged_in_api_client, factories, mocker, queryset_equal_queries
):
    url = reverse("api:subsonic-get_song")
    assert url.endswith("getSong") is True
    artist = factories["music.Artist"]()
    album = factories["music.Album"](artist=artist)
    track = factories["music.Track"](album=album, playable=True)
    upload = factories["music.Upload"](track=track)
    playable_by = mocker.spy(music_models.TrackQuerySet, "playable_by")
    response = logged_in_api_client.get(url, {"f": f, "id": track.pk})

    assert response.status_code == 200
    assert response.data == {
        "song": serializers.get_track_data(track.album, track, upload)
    }
    playable_by.assert_called_once_with(music_models.Track.objects.all(), None)


@pytest.mark.parametrize("f", ["json"])
def test_stream(
    f, db, logged_in_api_client, factories, mocker, queryset_equal_queries, settings
):
    # Even with this settings set to false, we proxy media in the subsonic API
    # Because clients don't expect a 302 redirect
    settings.PROXY_MEDIA = False
    url = reverse("api:subsonic-stream")
    mocked_serve = mocker.spy(music_views, "handle_serve")
    assert url.endswith("stream") is True
    upload = factories["music.Upload"](playable=True)
    playable_by = mocker.spy(music_models.TrackQuerySet, "playable_by")
    response = logged_in_api_client.get(url, {"f": f, "id": upload.track.pk})

    mocked_serve.assert_called_once_with(
        upload=upload,
        user=logged_in_api_client.user,
        format=None,
        max_bitrate=None,
        proxy_media=True,
        wsgi_request=response.wsgi_request,
    )
    assert response.status_code == 200
    playable_by.assert_called_once_with(music_models.Track.objects.all(), None)


@pytest.mark.parametrize("format,expected", [("mp3", "mp3"), ("raw", None)])
def test_stream_format(format, expected, logged_in_api_client, factories, mocker):
    url = reverse("api:subsonic-stream")
    mocked_serve = mocker.patch.object(
        music_views, "handle_serve", return_value=Response()
    )
    upload = factories["music.Upload"](playable=True)
    response = logged_in_api_client.get(url, {"id": upload.track.pk, "format": format})

    mocked_serve.assert_called_once_with(
        upload=upload,
        user=logged_in_api_client.user,
        format=expected,
        max_bitrate=None,
        proxy_media=True,
        wsgi_request=response.wsgi_request,
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    "max_bitrate,format,default_transcoding_format,expected_bitrate,expected_format",
    [
        # no max bitrate, no format, so no transcoding should happen
        (0, "", "ogg", None, None),
        # same using "raw" format
        (0, "raw", "ogg", None, None),
        # specified bitrate, but no format, so fallback to default transcoding format
        (192, "", "ogg", 192000, "ogg"),
        # specified bitrate, but over limit
        (2000, "", "ogg", 320000, "ogg"),
        # specified format, we use that one
        (192, "opus", "ogg", 192000, "opus"),
        # No default transcoding format set and no format requested
        (192, "", None, 192000, None),
    ],
)
def test_stream_transcode(
    max_bitrate,
    format,
    default_transcoding_format,
    expected_bitrate,
    expected_format,
    logged_in_api_client,
    factories,
    mocker,
    settings,
):
    upload = factories["music.Upload"](playable=True)
    params = {"id": upload.track.pk, "maxBitRate": max_bitrate}
    if format:
        params["format"] = format
    settings.SUBSONIC_DEFAULT_TRANSCODING_FORMAT = default_transcoding_format
    url = reverse("api:subsonic-stream")
    mocked_serve = mocker.patch.object(
        music_views, "handle_serve", return_value=Response()
    )
    response = logged_in_api_client.get(url, params)

    mocked_serve.assert_called_once_with(
        upload=upload,
        user=logged_in_api_client.user,
        format=expected_format,
        max_bitrate=expected_bitrate,
        proxy_media=True,
        wsgi_request=response.wsgi_request,
    )
    assert response.status_code == 200


@pytest.mark.parametrize("f", ["json"])
def test_star(f, db, logged_in_api_client, factories):
    url = reverse("api:subsonic-star")
    assert url.endswith("star") is True
    track = factories["music.Track"]()
    response = logged_in_api_client.get(url, {"f": f, "id": track.pk})

    assert response.status_code == 200
    assert response.data == {"status": "ok"}

    favorite = logged_in_api_client.user.track_favorites.latest("id")
    assert favorite.track == track


@pytest.mark.parametrize("f", ["json"])
def test_unstar(f, db, logged_in_api_client, factories):
    url = reverse("api:subsonic-unstar")
    assert url.endswith("unstar") is True
    track = factories["music.Track"]()
    factories["favorites.TrackFavorite"](track=track, user=logged_in_api_client.user)
    response = logged_in_api_client.get(url, {"f": f, "id": track.pk})

    assert response.status_code == 200
    assert response.data == {"status": "ok"}
    assert logged_in_api_client.user.track_favorites.count() == 0


@pytest.mark.parametrize("f", ["json"])
def test_get_starred2(f, db, logged_in_api_client, factories):
    url = reverse("api:subsonic-get_starred2")
    assert url.endswith("getStarred2") is True
    track = factories["music.Track"]()
    favorite = factories["favorites.TrackFavorite"](
        track=track, user=logged_in_api_client.user
    )
    response = logged_in_api_client.get(url, {"f": f, "id": track.pk})

    assert response.status_code == 200
    assert response.data == {
        "starred2": {"song": serializers.get_starred_tracks_data([favorite])}
    }


@pytest.mark.parametrize("f", ["json"])
def test_get_random_songs(f, db, logged_in_api_client, factories, mocker):
    url = reverse("api:subsonic-get_random_songs")
    assert url.endswith("getRandomSongs") is True
    track1 = factories["music.Track"]()
    track2 = factories["music.Track"]()
    factories["music.Track"]()

    order_by = mocker.patch.object(
        music_models.TrackQuerySet, "order_by", return_value=[track1, track2]
    )
    response = logged_in_api_client.get(url, {"f": f, "size": 2})

    assert response.status_code == 200
    assert response.data == {
        "randomSongs": {
            "song": serializers.GetSongSerializer([track1, track2], many=True).data
        }
    }

    order_by.assert_called_once_with("?")


@pytest.mark.parametrize("f", ["json"])
def test_get_genres(f, db, logged_in_api_client, factories, mocker):
    url = reverse("api:subsonic-get_genres")
    assert url.endswith("getGenres") is True
    tag1 = factories["tags.Tag"](name="Pop")
    tag2 = factories["tags.Tag"](name="Rock")

    factories["music.Album"](set_tags=[tag1.name, tag2.name])
    factories["music.Track"](set_tags=[tag1.name])
    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert response.data == {
        "genres": {
            "genre": [
                {"songCount": 1, "albumCount": 1, "value": tag1.name},
                {"songCount": 0, "albumCount": 1, "value": tag2.name},
            ]
        }
    }


@pytest.mark.parametrize("f", ["json"])
def test_get_starred(f, db, logged_in_api_client, factories):
    url = reverse("api:subsonic-get_starred")
    assert url.endswith("getStarred") is True
    track = factories["music.Track"]()
    favorite = factories["favorites.TrackFavorite"](
        track=track, user=logged_in_api_client.user
    )
    response = logged_in_api_client.get(url, {"f": f, "id": track.pk})

    assert response.status_code == 200
    assert response.data == {
        "starred": {"song": serializers.get_starred_tracks_data([favorite])}
    }


@pytest.mark.parametrize("f", ["json"])
def test_get_album_list2(
    f, db, logged_in_api_client, factories, mocker, queryset_equal_queries
):
    url = reverse("api:subsonic-get_album_list2")
    assert url.endswith("getAlbumList2") is True
    album1 = factories["music.Album"](playable=True)
    album2 = factories["music.Album"](playable=True)
    factories["music.Album"]()
    playable_by = mocker.spy(music_models.AlbumQuerySet, "playable_by")
    response = logged_in_api_client.get(url, {"f": f, "type": "newest"})

    assert response.status_code == 200
    assert response.data == {
        "albumList2": {"album": serializers.get_album_list2_data([album2, album1])}
    }
    playable_by.assert_called_once()


def test_get_album_list2_recent(db, logged_in_api_client, factories):
    url = reverse("api:subsonic-get_album_list2")
    assert url.endswith("getAlbumList2") is True
    factories["music.Album"](playable=True, release_date=None)
    album2 = factories["music.Album"](playable=True)
    album3 = factories["music.Album"](playable=True)
    response = logged_in_api_client.get(url, {"f": "json", "type": "recent"})

    assert response.status_code == 200
    expected_albums = reversed(sorted([album3, album2], key=lambda a: a.release_date))
    assert response.data == {
        "albumList2": {"album": serializers.get_album_list2_data(expected_albums)}
    }


@pytest.mark.parametrize("f", ["json"])
def test_get_album_list2_pagination(f, db, logged_in_api_client, factories):
    url = reverse("api:subsonic-get_album_list2")
    assert url.endswith("getAlbumList2") is True
    album1 = factories["music.Album"](playable=True)
    factories["music.Album"](playable=True)
    response = logged_in_api_client.get(
        url, {"f": f, "type": "newest", "size": 1, "offset": 1}
    )

    assert response.status_code == 200
    assert response.data == {
        "albumList2": {"album": serializers.get_album_list2_data([album1])}
    }


@pytest.mark.parametrize("f", ["json"])
def test_get_album_list2_by_genre(f, db, logged_in_api_client, factories):
    url = reverse("api:subsonic-get_album_list2")
    assert url.endswith("getAlbumList2") is True
    album1 = factories["music.Album"](
        artist__name="Artist1", playable=True, set_tags=["Rock"]
    )
    album2 = factories["music.Album"](
        artist__name="Artist2", playable=True, artist__set_tags=["Rock"]
    )
    factories["music.Album"](playable=True, set_tags=["Pop"])
    response = logged_in_api_client.get(
        url, {"f": f, "type": "byGenre", "size": 5, "offset": 0, "genre": "rock"}
    )

    assert response.status_code == 200
    assert response.data == {
        "albumList2": {"album": serializers.get_album_list2_data([album1, album2])}
    }


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"type": "byYear", "fromYear": 1902, "toYear": 1903}, [2, 3]),
        # Because why not, it's supported in Subsonic API…
        # http://www.subsonic.org/pages/api.jsp#getAlbumList2
        ({"type": "byYear", "fromYear": 1903, "toYear": 1902}, [3, 2]),
    ],
)
def test_get_album_list2_by_year(params, expected, db, logged_in_api_client, factories):
    albums = [
        factories["music.Album"](
            playable=True, release_date=datetime.date(1900 + i, 1, 1)
        )
        for i in range(5)
    ]
    url = reverse("api:subsonic-get_album_list2")
    base_params = {"f": "json"}
    base_params.update(params)
    response = logged_in_api_client.get(url, base_params)

    assert response.status_code == 200
    assert response.data == {
        "albumList2": {
            "album": serializers.get_album_list2_data([albums[i] for i in expected])
        }
    }


@pytest.mark.parametrize("f", ["json"])
@pytest.mark.parametrize(
    "tags_field",
    ["set_tags", "artist__set_tags", "album__set_tags", "album__artist__set_tags"],
)
def test_get_songs_by_genre(f, tags_field, db, logged_in_api_client, factories):
    url = reverse("api:subsonic-get_songs_by_genre")
    assert url.endswith("getSongsByGenre") is True
    track1 = factories["music.Track"](playable=True, **{tags_field: ["Rock"]})
    track2 = factories["music.Track"](playable=True, **{tags_field: ["Rock"]})
    factories["music.Track"](playable=True, **{tags_field: ["Pop"]})
    expected = {
        "songsByGenre": {"song": serializers.get_song_list_data([track2, track1])}
    }

    response = logged_in_api_client.get(
        url, {"f": f, "count": 5, "offset": 0, "genre": "rock"}
    )
    assert response.status_code == 200
    assert response.data == expected


def test_get_songs_by_genre_offset(logged_in_api_client, factories):
    url = reverse("api:subsonic-get_songs_by_genre")
    assert url.endswith("getSongsByGenre") is True
    track1 = factories["music.Track"](playable=True, set_tags=["Rock"])
    factories["music.Track"](playable=True, set_tags=["Rock"])
    factories["music.Track"](playable=True, set_tags=["Pop"])
    # the API order tracks by creation date DESC, so the second one
    # returned by the API is the first one to be created in the test.
    expected = {"songsByGenre": {"song": serializers.get_song_list_data([track1])}}

    response = logged_in_api_client.get(
        url, {"f": "json", "count": 1, "offset": 1, "genre": "rock"}
    )
    assert response.status_code == 200
    assert response.data == expected


@pytest.mark.parametrize("f", ["json"])
def test_search3(f, db, logged_in_api_client, factories):
    url = reverse("api:subsonic-search3")
    assert url.endswith("search3") is True
    artist = factories["music.Artist"](name="testvalue", playable=True)
    factories["music.Artist"](name="nope")
    factories["music.Artist"](name="nope2", playable=True)
    album = factories["music.Album"](title="testvalue", playable=True)
    factories["music.Album"](title="nope")
    factories["music.Album"](title="nope2", playable=True)
    track = factories["music.Track"](title="testvalue", playable=True)
    factories["music.Track"](title="nope")
    factories["music.Track"](title="nope2", playable=True)

    response = logged_in_api_client.get(url, {"f": f, "query": "testval"})

    artist_qs = (
        music_models.Artist.objects.with_albums_count()
        .filter(pk=artist.pk)
        .values("_albums_count", "id", "name")
    )
    assert response.status_code == 200
    assert response.data == {
        "searchResult3": {
            "artist": [serializers.get_artist_data(a) for a in artist_qs],
            "album": serializers.get_album_list2_data([album]),
            "song": serializers.get_song_list_data([track]),
        }
    }


@pytest.mark.parametrize("f", ["json"])
def test_get_playlists(f, db, logged_in_api_client, factories):
    url = reverse("api:subsonic-get_playlists")
    assert url.endswith("getPlaylists") is True
    playlist1 = factories["playlists.PlaylistTrack"](
        playlist__user=logged_in_api_client.user
    ).playlist
    playlist2 = factories["playlists.PlaylistTrack"](
        playlist__privacy_level="everyone"
    ).playlist
    playlist3 = factories["playlists.PlaylistTrack"](
        playlist__privacy_level="instance"
    ).playlist
    # private
    factories["playlists.PlaylistTrack"](playlist__privacy_level="me")
    # no track
    factories["playlists.Playlist"](privacy_level="everyone")
    response = logged_in_api_client.get(url, {"f": f})

    qs = (
        playlist1.__class__.objects.with_tracks_count()
        .filter(pk__in=[playlist1.pk, playlist2.pk, playlist3.pk])
        .order_by("-creation_date")
    )
    expected = {
        "playlists": {"playlist": [serializers.get_playlist_data(p) for p in qs]}
    }
    assert response.status_code == 200
    assert response.data == expected


@pytest.mark.parametrize("f", ["json"])
def test_get_playlist(f, db, logged_in_api_client, factories):
    url = reverse("api:subsonic-get_playlist")
    assert url.endswith("getPlaylist") is True
    playlist = factories["playlists.PlaylistTrack"](
        playlist__user=logged_in_api_client.user
    ).playlist
    response = logged_in_api_client.get(url, {"f": f, "id": playlist.pk})

    qs = playlist.__class__.objects.with_tracks_count()
    assert response.status_code == 200
    assert response.data == {
        "playlist": serializers.get_playlist_detail_data(qs.first())
    }


@pytest.mark.parametrize("f", ["json"])
def test_update_playlist(f, db, logged_in_api_client, factories):
    url = reverse("api:subsonic-update_playlist")
    assert url.endswith("updatePlaylist") is True
    playlist = factories["playlists.Playlist"](user=logged_in_api_client.user)
    factories["playlists.PlaylistTrack"](index=0, playlist=playlist)
    new_track = factories["music.Track"]()
    response = logged_in_api_client.get(
        url,
        {
            "f": f,
            "name": "new_name",
            "playlistId": playlist.pk,
            "songIdToAdd": new_track.pk,
            "songIndexToRemove": 0,
        },
    )
    playlist.refresh_from_db()
    assert response.status_code == 200
    assert playlist.name == "new_name"
    assert playlist.playlist_tracks.count() == 1
    assert playlist.playlist_tracks.first().track_id == new_track.pk


@pytest.mark.parametrize("f", ["json"])
def test_delete_playlist(f, db, logged_in_api_client, factories):
    url = reverse("api:subsonic-delete_playlist")
    assert url.endswith("deletePlaylist") is True
    playlist = factories["playlists.Playlist"](user=logged_in_api_client.user)
    response = logged_in_api_client.get(url, {"f": f, "id": playlist.pk})
    assert response.status_code == 200
    with pytest.raises(playlist.__class__.DoesNotExist):
        playlist.refresh_from_db()


@pytest.mark.parametrize("f", ["json"])
def test_create_playlist(f, db, logged_in_api_client, factories):
    url = reverse("api:subsonic-create_playlist")
    assert url.endswith("createPlaylist") is True
    track1 = factories["music.Track"]()
    track2 = factories["music.Track"]()
    response = logged_in_api_client.get(
        url, {"f": f, "name": "hello", "songId": [track1.pk, track2.pk]}
    )
    assert response.status_code == 200
    playlist = logged_in_api_client.user.playlists.latest("id")
    assert playlist.playlist_tracks.count() == 2
    for i, t in enumerate([track1, track2]):
        plt = playlist.playlist_tracks.get(track=t)
        assert plt.index == i
    assert playlist.name == "hello"
    qs = playlist.__class__.objects.with_tracks_count()
    assert response.data == {
        "playlist": serializers.get_playlist_detail_data(qs.first())
    }


@pytest.mark.parametrize("f", ["json"])
def test_get_music_folders(f, db, logged_in_api_client, factories):
    url = reverse("api:subsonic-get_music_folders")
    assert url.endswith("getMusicFolders") is True
    response = logged_in_api_client.get(url, {"f": f})
    assert response.status_code == 200
    assert response.data == {
        "musicFolders": {"musicFolder": [{"id": 1, "name": "Music"}]}
    }


@pytest.mark.parametrize("f", ["json"])
def test_get_indexes(
    f, db, logged_in_api_client, factories, mocker, queryset_equal_queries
):
    factories["moderation.UserFilter"](
        user=logged_in_api_client.user,
        target_artist=factories["music.Artist"](playable=True),
    )
    exclude_query = moderation_filters.get_filtered_content_query(
        moderation_filters.USER_FILTER_CONFIG["ARTIST"], logged_in_api_client.user
    )

    url = reverse("api:subsonic-get_indexes")
    assert url.endswith("getIndexes") is True
    factories["music.Artist"].create_batch(size=3, playable=True)
    expected = {
        "indexes": serializers.GetArtistsSerializer(
            music_models.Artist.objects.all().exclude(exclude_query)
        ).data
    }
    playable_by = mocker.spy(music_models.ArtistQuerySet, "playable_by")
    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert response.data == expected

    playable_by.assert_called_once_with(
        music_models.Artist.objects.all().exclude(exclude_query),
        logged_in_api_client.user.actor,
    )


def test_get_cover_art_album(factories, logged_in_api_client):
    url = reverse("api:subsonic-get_cover_art")
    assert url.endswith("getCoverArt") is True
    album = factories["music.Album"](with_cover=True)
    response = logged_in_api_client.get(url, {"id": "al-{}".format(album.pk)})

    assert response.status_code == 200
    assert response["Content-Type"] == ""
    assert response["X-Accel-Redirect"] == music_views.get_file_path(
        album.attachment_cover.file
    ).decode("utf-8")


def test_get_cover_art_attachment(factories, logged_in_api_client):
    attachment = factories["common.Attachment"]()
    url = reverse("api:subsonic-get_cover_art")
    assert url.endswith("getCoverArt") is True
    response = logged_in_api_client.get(url, {"id": "at-{}".format(attachment.uuid)})

    assert response.status_code == 200
    assert response["Content-Type"] == ""
    assert response["X-Accel-Redirect"] == music_views.get_file_path(
        attachment.file
    ).decode("utf-8")


def test_get_avatar(factories, logged_in_api_client):
    user = factories["users.User"]()
    url = reverse("api:subsonic-get_avatar")
    assert url.endswith("getAvatar") is True
    response = logged_in_api_client.get(url, {"username": user.username})

    assert response.status_code == 200
    assert response["Content-Type"] == ""
    assert response["X-Accel-Redirect"] == music_views.get_file_path(
        user.avatar
    ).decode("utf-8")


def test_scrobble(factories, logged_in_api_client):
    upload = factories["music.Upload"]()
    track = upload.track
    url = reverse("api:subsonic-scrobble")
    assert url.endswith("scrobble") is True
    response = logged_in_api_client.get(url, {"id": track.pk, "submission": True})

    assert response.status_code == 200

    listening = logged_in_api_client.user.listenings.latest("id")
    assert listening.track == track


@pytest.mark.parametrize("f", ["json"])
def test_get_user(f, db, logged_in_api_client, factories):
    url = reverse("api:subsonic-get_user")
    assert url.endswith("getUser") is True
    response = logged_in_api_client.get(
        url, {"f": f, "username": logged_in_api_client.user.username}
    )
    assert response.status_code == 200
    assert response.data == {
        "user": {
            "username": logged_in_api_client.user.username,
            "email": logged_in_api_client.user.email,
            "scrobblingEnabled": "true",
            "adminRole": "false",
            "downloadRole": "true",
            "uploadRole": "true",
            "settingsRole": "false",
            "playlistRole": "true",
            "commentRole": "false",
            "podcastRole": "true",
            "streamRole": "true",
            "jukeboxRole": "true",
            "coverArtRole": "false",
            "shareRole": "false",
            "folder": [
                {"value": f["id"]}
                for f in serializers.get_folders(logged_in_api_client.user)
            ],
        }
    }


def test_create_podcast_channel(logged_in_api_client, factories, mocker):
    channel = factories["audio.Channel"](external=True)
    rss_url = "https://rss.url/"
    get_channel_from_rss_url = mocker.patch(
        "funkwhale_api.audio.serializers.get_channel_from_rss_url",
        return_value=(channel, []),
    )
    actor = logged_in_api_client.user.create_actor()
    url = reverse("api:subsonic-create_podcast_channel")
    assert url.endswith("createPodcastChannel") is True
    response = logged_in_api_client.get(url, {"f": "json", "url": rss_url})
    assert response.status_code == 200
    assert response.data == {"status": "ok"}

    subscription = actor.emitted_follows.get(target=channel.actor)
    assert subscription.approved is True
    get_channel_from_rss_url.assert_called_once_with(rss_url)


def test_delete_podcast_channel(logged_in_api_client, factories, mocker):
    actor = logged_in_api_client.user.create_actor()
    channel = factories["audio.Channel"](external=True)
    subscription = factories["federation.Follow"](actor=actor, target=channel.actor)
    other_subscription = factories["federation.Follow"](target=channel.actor)
    url = reverse("api:subsonic-delete_podcast_channel")
    assert url.endswith("deletePodcastChannel") is True
    response = logged_in_api_client.get(url, {"f": "json", "id": channel.uuid})
    assert response.status_code == 200
    assert response.data == {"status": "ok"}
    other_subscription.refresh_from_db()
    with pytest.raises(subscription.DoesNotExist):
        subscription.refresh_from_db()


def test_get_podcasts(logged_in_api_client, factories, mocker):
    actor = logged_in_api_client.user.create_actor()
    channel = factories["audio.Channel"](
        external=True, library__privacy_level="everyone"
    )
    upload1 = factories["music.Upload"](
        playable=True,
        track__artist=channel.artist,
        library=channel.library,
        bitrate=128000,
        duration=42,
    )
    upload2 = factories["music.Upload"](
        playable=True,
        track__artist=channel.artist,
        library=channel.library,
        bitrate=256000,
        duration=43,
    )
    factories["federation.Follow"](actor=actor, target=channel.actor, approved=True)
    factories["music.Upload"](import_status="pending", track__artist=channel.artist)
    factories["audio.Channel"](external=True)
    factories["federation.Follow"]()
    url = reverse("api:subsonic-get_podcasts")
    assert url.endswith("getPodcasts") is True
    response = logged_in_api_client.get(url, {"f": "json"})
    assert response.status_code == 200
    assert response.data == {
        "podcasts": {
            "channel": [serializers.get_channel_data(channel, [upload2, upload1])],
        }
    }


def test_get_podcasts_by_id(logged_in_api_client, factories, mocker):
    actor = logged_in_api_client.user.create_actor()
    channel1 = factories["audio.Channel"](
        external=True, library__privacy_level="everyone"
    )
    channel2 = factories["audio.Channel"](
        external=True, library__privacy_level="everyone"
    )
    upload1 = factories["music.Upload"](
        playable=True,
        track__artist=channel1.artist,
        library=channel1.library,
        bitrate=128000,
        duration=42,
    )
    factories["music.Upload"](
        playable=True,
        track__artist=channel2.artist,
        library=channel2.library,
        bitrate=256000,
        duration=43,
    )
    factories["federation.Follow"](actor=actor, target=channel1.actor, approved=True)
    factories["federation.Follow"](actor=actor, target=channel2.actor, approved=True)
    url = reverse("api:subsonic-get_podcasts")
    assert url.endswith("getPodcasts") is True
    response = logged_in_api_client.get(url, {"f": "json", "id": channel1.uuid})
    assert response.status_code == 200
    assert response.data == {
        "podcasts": {"channel": [serializers.get_channel_data(channel1, [upload1])]}
    }


def test_get_newest_podcasts(logged_in_api_client, factories, mocker):
    actor = logged_in_api_client.user.create_actor()
    channel = factories["audio.Channel"](
        external=True, library__privacy_level="everyone"
    )
    upload1 = factories["music.Upload"](
        playable=True,
        track__artist=channel.artist,
        library=channel.library,
        bitrate=128000,
        duration=42,
    )
    upload2 = factories["music.Upload"](
        playable=True,
        track__artist=channel.artist,
        library=channel.library,
        bitrate=256000,
        duration=43,
    )
    factories["federation.Follow"](actor=actor, target=channel.actor, approved=True)
    url = reverse("api:subsonic-get_newest_podcasts")
    assert url.endswith("getNewestPodcasts") is True
    response = logged_in_api_client.get(url, {"f": "json"})
    assert response.status_code == 200
    assert response.data == {
        "newestPodcasts": {
            "episode": [
                serializers.get_channel_episode_data(upload, channel.uuid)
                for upload in [upload2, upload1]
            ],
        }
    }

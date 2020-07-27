import pytest
from django.urls import reverse

from funkwhale_api.playlists import models


def test_can_create_playlist_via_api(logged_in_api_client):
    url = reverse("api:v1:playlists-list")
    data = {"name": "test", "privacy_level": "everyone"}

    logged_in_api_client.post(url, data)

    playlist = logged_in_api_client.user.playlists.latest("id")
    assert playlist.name == "test"
    assert playlist.privacy_level == "everyone"


def test_serializer_includes_tracks_count(factories, logged_in_api_client):
    playlist = factories["playlists.Playlist"]()
    factories["playlists.PlaylistTrack"](playlist=playlist)

    url = reverse("api:v1:playlists-detail", kwargs={"pk": playlist.pk})
    response = logged_in_api_client.get(url)

    assert response.data["tracks_count"] == 1


def test_serializer_includes_tracks_count_986(factories, logged_in_api_client):
    playlist = factories["playlists.Playlist"]()
    plt = factories["playlists.PlaylistTrack"](playlist=playlist)
    factories["music.Upload"].create_batch(
        3, track=plt.track, library__privacy_level="everyone", import_status="finished"
    )
    url = reverse("api:v1:playlists-detail", kwargs={"pk": playlist.pk})
    response = logged_in_api_client.get(url)

    assert response.data["tracks_count"] == 1


def test_serializer_includes_is_playable(factories, logged_in_api_client):
    playlist = factories["playlists.Playlist"]()
    factories["playlists.PlaylistTrack"](playlist=playlist)

    url = reverse("api:v1:playlists-detail", kwargs={"pk": playlist.pk})
    response = logged_in_api_client.get(url)

    assert response.data["is_playable"] is False


def test_playlist_inherits_user_privacy(logged_in_api_client):
    url = reverse("api:v1:playlists-list")
    user = logged_in_api_client.user
    user.privacy_level = "me"
    user.save()

    data = {"name": "test"}

    logged_in_api_client.post(url, data)
    playlist = user.playlists.latest("id")
    assert playlist.privacy_level == user.privacy_level


@pytest.mark.parametrize(
    "name,method", [("api:v1:playlists-list", "post")],
)
def test_url_requires_login(name, method, factories, api_client):
    url = reverse(name)

    response = getattr(api_client, method)(url, {})

    assert response.status_code == 401


def test_only_can_add_track_on_own_playlist_via_api(factories, logged_in_api_client):
    track = factories["music.Track"]()
    playlist = factories["playlists.Playlist"]()
    url = reverse("api:v1:playlists-add", kwargs={"pk": playlist.pk})
    data = {"tracks": [track.pk]}

    response = logged_in_api_client.post(url, data, format="json")
    assert response.status_code == 404
    assert playlist.playlist_tracks.count() == 0


def test_deleting_plt_updates_indexes(mocker, factories, logged_in_api_client):
    remove = mocker.spy(models.Playlist, "remove")
    factories["music.Track"]()
    playlist = factories["playlists.Playlist"](user=logged_in_api_client.user)
    plt0 = factories["playlists.PlaylistTrack"](index=0, playlist=playlist)
    plt1 = factories["playlists.PlaylistTrack"](index=1, playlist=playlist)
    url = reverse("api:v1:playlists-remove", kwargs={"pk": playlist.pk})

    response = logged_in_api_client.delete(url, {"index": 0})

    assert response.status_code == 204
    remove.assert_called_once_with(plt0.playlist, 0)
    with pytest.raises(plt0.DoesNotExist):
        plt0.refresh_from_db()
    plt1.refresh_from_db()
    assert plt1.index == 0


@pytest.mark.parametrize("level", ["instance", "me", "followers"])
def test_playlist_privacy_respected_in_list_anon(
    preferences, level, factories, api_client
):
    preferences["common__api_authentication_required"] = False
    factories["playlists.Playlist"](privacy_level=level)
    url = reverse("api:v1:playlists-list")
    response = api_client.get(url)

    assert response.data["count"] == 0


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE"])
def test_only_owner_can_edit_playlist(method, factories, logged_in_api_client):
    playlist = factories["playlists.Playlist"]()
    url = reverse("api:v1:playlists-detail", kwargs={"pk": playlist.pk})
    response = getattr(logged_in_api_client, method.lower())(url)

    assert response.status_code == 404


def test_can_add_multiple_tracks_at_once_via_api(
    factories, mocker, logged_in_api_client
):
    playlist = factories["playlists.Playlist"](user=logged_in_api_client.user)
    tracks = factories["music.Track"].create_batch(size=5)
    track_ids = [t.id for t in tracks]
    mocker.spy(playlist, "insert_many")
    url = reverse("api:v1:playlists-add", kwargs={"pk": playlist.pk})
    response = logged_in_api_client.post(url, {"tracks": track_ids})

    assert response.status_code == 201
    assert playlist.playlist_tracks.count() == len(track_ids)

    for plt in playlist.playlist_tracks.order_by("index"):
        assert response.data["results"][plt.index]["index"] == plt.index
        assert plt.track == tracks[plt.index]


def test_honor_max_playlist_size(factories, mocker, logged_in_api_client, preferences):
    preferences["playlists__max_tracks"] = 3
    playlist = factories["playlists.Playlist"](user=logged_in_api_client.user)
    tracks = factories["music.Track"].create_batch(
        size=preferences["playlists__max_tracks"] + 1
    )
    track_ids = [t.id for t in tracks]
    mocker.spy(playlist, "insert_many")
    url = reverse("api:v1:playlists-add", kwargs={"pk": playlist.pk})
    response = logged_in_api_client.post(url, {"tracks": track_ids})

    assert response.status_code == 400


def test_can_clear_playlist_from_api(factories, mocker, logged_in_api_client):
    playlist = factories["playlists.Playlist"](user=logged_in_api_client.user)
    factories["playlists.PlaylistTrack"].create_batch(size=5, playlist=playlist)
    url = reverse("api:v1:playlists-clear", kwargs={"pk": playlist.pk})
    response = logged_in_api_client.delete(url)

    assert response.status_code == 204
    assert playlist.playlist_tracks.count() == 0


def test_update_playlist_from_api(factories, mocker, logged_in_api_client):
    playlist = factories["playlists.Playlist"](user=logged_in_api_client.user)
    factories["playlists.PlaylistTrack"].create_batch(size=5, playlist=playlist)
    url = reverse("api:v1:playlists-detail", kwargs={"pk": playlist.pk})
    response = logged_in_api_client.patch(url, {"name": "test"})
    playlist.refresh_from_db()

    assert response.status_code == 200
    assert response.data["user"]["username"] == playlist.user.username


def test_move_plt_updates_indexes(mocker, factories, logged_in_api_client):
    playlist = factories["playlists.Playlist"](user=logged_in_api_client.user)
    plt0 = factories["playlists.PlaylistTrack"](index=0, playlist=playlist)
    plt1 = factories["playlists.PlaylistTrack"](index=1, playlist=playlist)
    url = reverse("api:v1:playlists-move", kwargs={"pk": playlist.pk})

    response = logged_in_api_client.post(url, {"from": 1, "to": 0})

    assert response.status_code == 204

    plt0.refresh_from_db()
    plt1.refresh_from_db()
    assert plt0.index == 1
    assert plt1.index == 0

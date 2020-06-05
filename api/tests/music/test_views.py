import datetime
import io
import magic
import os
import urllib.parse
import uuid

import pytest
from django.db.models import Prefetch
from django.urls import reverse
from django.utils import timezone

from funkwhale_api.common import utils
from funkwhale_api.federation import api_serializers as federation_api_serializers
from funkwhale_api.federation import utils as federation_utils
from funkwhale_api.federation import tasks as federation_tasks
from funkwhale_api.music import licenses, models, serializers, tasks, views
from funkwhale_api.users import authentication as users_authentication

DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def test_artist_list_serializer(api_request, factories, logged_in_api_client):
    tags = ["tag1", "tag2"]
    track = factories["music.Upload"](
        library__privacy_level="everyone",
        import_status="finished",
        track__album__artist__set_tags=tags,
    ).track
    artist = track.artist
    request = api_request.get("/")
    qs = artist.__class__.objects.with_albums().prefetch_related(
        Prefetch("tracks", to_attr="_prefetched_tracks")
    )
    serializer = serializers.ArtistWithAlbumsSerializer(
        qs, many=True, context={"request": request}
    )
    expected = {"count": 1, "next": None, "previous": None, "results": serializer.data}
    for artist in serializer.data:
        artist["tags"] = tags
        for album in artist["albums"]:
            album["is_playable"] = True

    url = reverse("api:v1:artists-list")
    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert response.data == expected


def test_album_list_serializer(api_request, factories, logged_in_api_client):
    tags = ["tag1", "tag2"]
    track = factories["music.Upload"](
        library__privacy_level="everyone",
        import_status="finished",
        track__album__set_tags=tags,
    ).track
    album = track.album
    request = api_request.get("/")
    qs = album.__class__.objects.with_prefetched_tracks_and_playable_uploads(None)
    serializer = serializers.AlbumSerializer(
        qs, many=True, context={"request": request}
    )
    expected = {"count": 1, "next": None, "previous": None, "results": serializer.data}
    for album in serializer.data:
        album["tags"] = tags
    url = reverse("api:v1:albums-list")
    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert response.data["results"][0] == expected["results"][0]


def test_track_list_serializer(api_request, factories, logged_in_api_client):
    tags = ["tag1", "tag2"]
    track = factories["music.Upload"](
        library__privacy_level="everyone",
        import_status="finished",
        track__set_tags=tags,
    ).track
    request = api_request.get("/")
    qs = track.__class__.objects.with_playable_uploads(None)
    serializer = serializers.TrackSerializer(
        qs, many=True, context={"request": request}
    )
    expected = {"count": 1, "next": None, "previous": None, "results": serializer.data}
    for track in serializer.data:
        track["tags"] = tags
    url = reverse("api:v1:tracks-list")
    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert response.data == expected


def test_track_list_filter_id(api_request, factories, logged_in_api_client):
    track1 = factories["music.Track"]()
    track2 = factories["music.Track"]()
    factories["music.Track"]()
    url = reverse("api:v1:tracks-list")
    response = logged_in_api_client.get(url, {"id[]": [track1.id, track2.id]})

    assert response.status_code == 200
    assert response.data["count"] == 2
    assert response.data["results"][0]["id"] == track2.id
    assert response.data["results"][1]["id"] == track1.id


@pytest.mark.parametrize("param,expected", [("true", "full"), ("false", "empty")])
def test_artist_view_filter_playable(param, expected, factories, api_request):
    artists = {
        "empty": factories["music.Artist"](),
        "full": factories["music.Upload"](
            library__privacy_level="everyone", import_status="finished"
        ).track.artist,
    }

    request = api_request.get("/", {"playable": param})
    view = views.ArtistViewSet()
    view.action_map = {"get": "list"}
    expected = [artists[expected]]
    view.request = view.initialize_request(request)
    queryset = view.filter_queryset(view.get_queryset())

    assert list(queryset) == expected


@pytest.mark.parametrize("param,expected", [("true", "full"), ("false", "empty")])
def test_album_view_filter_playable(param, expected, factories, api_request):
    artists = {
        "empty": factories["music.Album"](),
        "full": factories["music.Upload"](
            library__privacy_level="everyone", import_status="finished"
        ).track.album,
    }

    request = api_request.get("/", {"playable": param})
    view = views.AlbumViewSet()
    view.action_map = {"get": "list"}
    expected = [artists[expected]]
    view.request = view.initialize_request(request)
    queryset = view.filter_queryset(view.get_queryset())

    assert list(queryset) == expected


@pytest.mark.parametrize(
    "param", [("I've Got"), ("Français"), ("I've Got Everything : Spoken Word Poetry")]
)
def test_album_view_filter_query(param, factories, api_request):
    # Test both partial and full search.
    factories["music.Album"](title="I've Got Nothing : Original Soundtrack")
    factories["music.Album"](title="I've Got Cake : Remix")
    factories["music.Album"](title="Français Et Tu")
    factories["music.Album"](title="I've Got Everything : Spoken Word Poetry")

    request = api_request.get("/", {"q": param})
    view = views.AlbumViewSet()
    view.action_map = {"get": "list"}
    view.request = view.initialize_request(request)
    queryset = view.filter_queryset(view.get_queryset())

    # Loop through our "expected list", and assert some string finds against our param.
    for val in list(queryset):
        assert val.title.find(param) != -1


def test_can_serve_upload_as_remote_library(
    factories, authenticated_actor, logged_in_api_client, settings, preferences
):
    preferences["common__api_authentication_required"] = True
    upload = factories["music.Upload"](
        library__privacy_level="everyone", import_status="finished"
    )
    library_actor = upload.library.actor
    factories["federation.Follow"](
        approved=True, actor=authenticated_actor, target=library_actor
    )

    response = logged_in_api_client.get(upload.track.listen_url)

    assert response.status_code == 200
    assert response["X-Accel-Redirect"] == "{}{}".format(
        settings.PROTECT_FILES_PATH,
        views.strip_absolute_media_url(upload.audio_file.url),
    )


def test_can_serve_upload_as_remote_library_deny_not_following(
    factories, authenticated_actor, settings, api_client, preferences
):
    preferences["common__api_authentication_required"] = True
    upload = factories["music.Upload"](
        import_status="finished", library__privacy_level="instance"
    )
    response = api_client.get(upload.track.listen_url)

    assert response.status_code == 404


@pytest.mark.parametrize(
    "proxy,serve_path,expected",
    [
        ("apache2", "/host/music", "/host/music/hello/world.mp3"),
        ("apache2", "/app/music", "/app/music/hello/world.mp3"),
        ("nginx", "/host/music", "/_protected/music/hello/world.mp3"),
        ("nginx", "/app/music", "/_protected/music/hello/world.mp3"),
    ],
)
def test_serve_file_in_place(
    proxy, serve_path, expected, factories, api_client, preferences, settings
):
    headers = {"apache2": "X-Sendfile", "nginx": "X-Accel-Redirect"}
    preferences["common__api_authentication_required"] = False
    settings.PROTECT_FILE_PATH = "/_protected/music"
    settings.REVERSE_PROXY_TYPE = proxy
    settings.MUSIC_DIRECTORY_PATH = "/app/music"
    settings.MUSIC_DIRECTORY_SERVE_PATH = serve_path
    upload = factories["music.Upload"](
        in_place=True,
        import_status="finished",
        source="file:///app/music/hello/world.mp3",
        library__privacy_level="everyone",
    )
    response = api_client.get(upload.track.listen_url)

    assert response.status_code == 200
    assert response[headers[proxy]] == expected


def test_serve_file_in_place_nginx_encode_url(
    factories, api_client, preferences, settings
):
    preferences["common__api_authentication_required"] = False
    settings.PROTECT_FILE_PATH = "/_protected/music"
    settings.REVERSE_PROXY_TYPE = "nginx"
    settings.MUSIC_DIRECTORY_PATH = "/app/music"
    settings.MUSIC_DIRECTORY_SERVE_PATH = "/app/music"
    upload = factories["music.Upload"](
        in_place=True,
        import_status="finished",
        source="file:///app/music/hello/world%?.mp3",
        library__privacy_level="everyone",
    )
    response = api_client.get(upload.track.listen_url)
    expected = "/_protected/music/hello/world%25%3F.mp3"

    assert response.status_code == 200
    assert response["X-Accel-Redirect"] == expected


def test_serve_s3_nginx_encode_url(mocker, settings):
    settings.PROTECT_FILE_PATH = "/_protected/media"
    settings.REVERSE_PROXY_TYPE = "nginx"
    audio_file = mocker.Mock(url="https://s3.storage.example/path/to/mp3?aws=signature")

    expected = (
        b"/_protected/media/https://s3.storage.example/path/to/mp3%3Faws%3Dsignature"
    )

    assert views.get_file_path(audio_file) == expected


@pytest.mark.parametrize(
    "proxy,serve_path,expected",
    [
        ("apache2", "/host/music", "/host/music/hello/worldéà.mp3"),
        ("apache2", "/app/music", "/app/music/hello/worldéà.mp3"),
        ("nginx", "/host/music", "/_protected/music/hello/world%C3%A9%C3%A0.mp3"),
        ("nginx", "/app/music", "/_protected/music/hello/world%C3%A9%C3%A0.mp3"),
    ],
)
def test_serve_file_in_place_utf8(
    proxy, serve_path, expected, factories, api_client, settings, preferences
):
    preferences["common__api_authentication_required"] = False
    settings.PROTECT_FILE_PATH = "/_protected/music"
    settings.REVERSE_PROXY_TYPE = proxy
    settings.MUSIC_DIRECTORY_PATH = "/app/music"
    settings.MUSIC_DIRECTORY_SERVE_PATH = serve_path
    path = views.get_file_path("/app/music/hello/worldéà.mp3")

    assert path == expected.encode("utf-8")


@pytest.mark.parametrize(
    "proxy,serve_path,expected",
    [
        ("apache2", "/host/music", "/host/media/tracks/hello/world.mp3"),
        # apache with container not supported yet
        # ('apache2', '/app/music', '/app/music/tracks/hello/world.mp3'),
        ("nginx", "/host/music", "/_protected/media/tracks/hello/world.mp3"),
        ("nginx", "/app/music", "/_protected/media/tracks/hello/world.mp3"),
    ],
)
def test_serve_file_media(
    proxy, serve_path, expected, factories, api_client, settings, preferences
):
    headers = {"apache2": "X-Sendfile", "nginx": "X-Accel-Redirect"}
    preferences["common__api_authentication_required"] = False
    settings.MEDIA_ROOT = "/host/media"
    settings.PROTECT_FILE_PATH = "/_protected/music"
    settings.REVERSE_PROXY_TYPE = proxy
    settings.MUSIC_DIRECTORY_PATH = "/app/music"
    settings.MUSIC_DIRECTORY_SERVE_PATH = serve_path

    upload = factories["music.Upload"](
        library__privacy_level="everyone", import_status="finished"
    )
    upload.__class__.objects.filter(pk=upload.pk).update(
        audio_file="tracks/hello/world.mp3"
    )
    response = api_client.get(upload.track.listen_url)

    assert response.status_code == 200
    assert response[headers[proxy]] == expected


def test_can_proxy_remote_track(factories, settings, api_client, r_mock, preferences):
    preferences["common__api_authentication_required"] = False
    url = "https://file.test"
    upload = factories["music.Upload"](
        library__privacy_level="everyone",
        audio_file="",
        source=url,
        import_status="finished",
    )

    r_mock.get(url, body=io.BytesIO(b"test"))
    response = api_client.get(upload.track.listen_url)
    upload.refresh_from_db()

    assert response.status_code == 200
    assert response["X-Accel-Redirect"] == "{}{}".format(
        settings.PROTECT_FILES_PATH,
        views.strip_absolute_media_url(upload.audio_file.url),
    )
    assert upload.audio_file.read() == b"test"


def test_serve_updates_access_date(factories, settings, api_client, preferences):
    preferences["common__api_authentication_required"] = False
    upload = factories["music.Upload"](
        library__privacy_level="everyone", import_status="finished"
    )
    now = timezone.now()
    assert upload.accessed_date is None

    response = api_client.get(upload.track.listen_url)
    upload.refresh_from_db()

    assert response.status_code == 200
    assert upload.accessed_date > now


def test_listen_no_track(factories, logged_in_api_client, mocker):
    increment_downloads_count = mocker.patch(
        "funkwhale_api.music.utils.increment_downloads_count"
    )

    url = reverse("api:v1:listen-detail", kwargs={"uuid": "noop"})
    response = logged_in_api_client.get(url)

    assert response.status_code == 404
    increment_downloads_count.call_count == 0


def test_listen_no_file(factories, logged_in_api_client):
    track = factories["music.Track"]()
    url = reverse("api:v1:listen-detail", kwargs={"uuid": track.uuid})
    response = logged_in_api_client.get(url)

    assert response.status_code == 404


def test_listen_no_available_file(factories, logged_in_api_client):
    upload = factories["music.Upload"]()
    url = reverse("api:v1:listen-detail", kwargs={"uuid": upload.track.uuid})
    response = logged_in_api_client.get(url)

    assert response.status_code == 404


def test_listen_correct_access(factories, logged_in_api_client, mocker):
    increment_downloads_count = mocker.patch(
        "funkwhale_api.music.utils.increment_downloads_count"
    )
    logged_in_api_client.user.create_actor()
    upload = factories["music.Upload"](
        library__actor=logged_in_api_client.user.actor,
        library__privacy_level="me",
        import_status="finished",
    )
    expected_filename = upload.track.full_name + ".ogg"
    url = reverse("api:v1:listen-detail", kwargs={"uuid": upload.track.uuid})
    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert response["Content-Disposition"] == "attachment; filename*=UTF-8''{}".format(
        urllib.parse.quote(expected_filename)
    )

    increment_downloads_count.assert_called_once_with(
        upload=upload,
        user=logged_in_api_client.user,
        wsgi_request=response.wsgi_request,
    )


def test_listen_correct_access_download_false(factories, logged_in_api_client):
    logged_in_api_client.user.create_actor()
    upload = factories["music.Upload"](
        library__actor=logged_in_api_client.user.actor,
        library__privacy_level="me",
        import_status="finished",
    )
    url = reverse("api:v1:listen-detail", kwargs={"uuid": upload.track.uuid})
    response = logged_in_api_client.get(url, {"download": "false"})

    assert response.status_code == 200
    assert "Content-Disposition" not in response


def test_listen_explicit_file(factories, logged_in_api_client, mocker, settings):
    mocked_serve = mocker.spy(views, "handle_serve")
    upload1 = factories["music.Upload"](
        library__privacy_level="everyone", import_status="finished"
    )
    upload2 = factories["music.Upload"](
        library__privacy_level="everyone", track=upload1.track, import_status="finished"
    )
    url = reverse("api:v1:listen-detail", kwargs={"uuid": upload2.track.uuid})
    response = logged_in_api_client.get(url, {"upload": upload2.uuid})

    assert response.status_code == 200
    mocked_serve.assert_called_once_with(
        upload=upload2,
        user=logged_in_api_client.user,
        format=None,
        max_bitrate=None,
        proxy_media=settings.PROXY_MEDIA,
        download=True,
        wsgi_request=response.wsgi_request,
    )


def test_listen_no_proxy(factories, logged_in_api_client, settings):
    settings.PROXY_MEDIA = False
    upload = factories["music.Upload"](
        library__privacy_level="everyone", import_status="finished"
    )
    url = reverse("api:v1:listen-detail", kwargs={"uuid": upload.track.uuid})
    response = logged_in_api_client.get(url, {"upload": upload.uuid})

    assert response.status_code == 302
    assert response["Location"] == upload.audio_file.url


@pytest.mark.parametrize(
    "mimetype,format,expected",
    [
        # already in proper format
        ("audio/mpeg", "mp3", False),
        # empty mimetype / format
        (None, "mp3", False),
        ("audio/mpeg", None, False),
        # unsupported format
        ("audio/mpeg", "noop", False),
        # should transcode
        ("audio/mpeg", "ogg", True),
    ],
)
def test_should_transcode(mimetype, format, expected, factories):
    upload = models.Upload(mimetype=mimetype)
    assert views.should_transcode(upload, format) is expected


@pytest.mark.parametrize(
    "bitrate,max_bitrate,expected",
    [
        # already in acceptable bitrate
        (192000, 320000, False),
        # No max bitrate specified
        (192000, None, False),
        # requested max below available
        (192000, 128000, True),
    ],
)
def test_should_transcode_bitrate(bitrate, max_bitrate, expected, factories):
    upload = models.Upload(mimetype="audio/mpeg", bitrate=bitrate)
    assert views.should_transcode(upload, "mp3", max_bitrate=max_bitrate) is expected


@pytest.mark.parametrize("value", [True, False])
def test_should_transcode_according_to_preference(value, preferences, factories):
    upload = models.Upload(mimetype="audio/ogg")
    expected = value
    preferences["music__transcoding_enabled"] = value

    assert views.should_transcode(upload, "mp3") is expected


def test_handle_serve_create_mp3_version(factories, now, mocker):
    mocker.patch("funkwhale_api.music.utils.increment_downloads_count")
    user = factories["users.User"]()
    upload = factories["music.Upload"](bitrate=42)
    response = views.handle_serve(
        upload=upload, user=user, format="mp3", wsgi_request=None
    )
    expected_filename = upload.track.full_name + ".mp3"
    version = upload.versions.latest("id")

    assert version.mimetype == "audio/mpeg"
    assert version.accessed_date == now
    assert version.bitrate == upload.bitrate
    assert version.audio_file_path.endswith(".mp3")
    assert version.size == version.audio_file.size
    assert magic.from_buffer(version.audio_file.read(), mime=True) == "audio/mpeg"
    assert response["Content-Disposition"] == "attachment; filename*=UTF-8''{}".format(
        urllib.parse.quote(expected_filename)
    )
    assert response.status_code == 200


def test_listen_transcode(factories, now, logged_in_api_client, mocker, settings):
    upload = factories["music.Upload"](
        import_status="finished", library__actor__user=logged_in_api_client.user
    )
    url = reverse("api:v1:listen-detail", kwargs={"uuid": upload.track.uuid})
    handle_serve = mocker.spy(views, "handle_serve")
    response = logged_in_api_client.get(url, {"to": "mp3"})

    assert response.status_code == 200

    handle_serve.assert_called_once_with(
        upload=upload,
        user=logged_in_api_client.user,
        format="mp3",
        max_bitrate=None,
        proxy_media=settings.PROXY_MEDIA,
        download=True,
        wsgi_request=response.wsgi_request,
    )


@pytest.mark.parametrize(
    "max_bitrate, expected",
    [
        ("", None),
        ("", None),
        ("-1", None),
        ("128", 128000),
        ("320", 320000),
        ("460", 320000),
    ],
)
def test_listen_transcode_bitrate(
    max_bitrate, expected, factories, now, logged_in_api_client, mocker, settings
):
    upload = factories["music.Upload"](
        import_status="finished", library__actor__user=logged_in_api_client.user
    )
    url = reverse("api:v1:listen-detail", kwargs={"uuid": upload.track.uuid})
    handle_serve = mocker.spy(views, "handle_serve")
    response = logged_in_api_client.get(url, {"max_bitrate": max_bitrate})

    assert response.status_code == 200

    handle_serve.assert_called_once_with(
        upload=upload,
        user=logged_in_api_client.user,
        format=None,
        max_bitrate=expected,
        proxy_media=settings.PROXY_MEDIA,
        download=True,
        wsgi_request=response.wsgi_request,
    )


@pytest.mark.parametrize("serve_path", [("/host/music",), ("/app/music",)])
def test_listen_transcode_in_place(
    serve_path, factories, now, logged_in_api_client, mocker, settings
):
    settings.MUSIC_DIRECTORY_PATH = "/app/music"
    settings.MUSIC_DIRECTORY_SERVE_PATH = serve_path
    upload = factories["music.Upload"](
        import_status="finished",
        library__actor__user=logged_in_api_client.user,
        audio_file=None,
        source="file://" + os.path.join(DATA_DIR, "test.ogg"),
    )

    assert upload.get_audio_segment()

    url = reverse("api:v1:listen-detail", kwargs={"uuid": upload.track.uuid})
    handle_serve = mocker.spy(views, "handle_serve")
    response = logged_in_api_client.get(url, {"to": "mp3"})

    assert response.status_code == 200

    handle_serve.assert_called_once_with(
        upload=upload,
        user=logged_in_api_client.user,
        format="mp3",
        max_bitrate=None,
        proxy_media=settings.PROXY_MEDIA,
        download=True,
        wsgi_request=response.wsgi_request,
    )


def test_user_can_create_library(factories, logged_in_api_client):
    actor = logged_in_api_client.user.create_actor()
    url = reverse("api:v1:libraries-list")

    response = logged_in_api_client.post(
        url, {"name": "hello", "description": "world", "privacy_level": "me"}
    )
    library = actor.libraries.first()

    assert response.status_code == 201

    assert library.actor == actor
    assert library.name == "hello"
    assert library.description == "world"
    assert library.privacy_level == "me"
    assert library.fid == library.get_federation_id()
    assert library.followers_url == library.fid + "/followers"


def test_user_can_list_their_library(factories, logged_in_api_client):
    actor = logged_in_api_client.user.create_actor()
    library = factories["music.Library"](actor=actor)
    factories["music.Library"](privacy_level="everyone")

    url = reverse("api:v1:libraries-list")
    response = logged_in_api_client.get(url, {"scope": "me"})

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["uuid"] == str(library.uuid)


def test_user_can_retrieve_another_user_library(factories, logged_in_api_client):
    library = factories["music.Library"]()

    url = reverse("api:v1:libraries-detail", kwargs={"uuid": library.uuid})
    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert response.data["uuid"] == str(library.uuid)


def test_user_can_list_public_libraries(factories, api_client, preferences):
    preferences["common__api_authentication_required"] = False
    library = factories["music.Library"](privacy_level="everyone")
    factories["music.Library"](privacy_level="me")

    url = reverse("api:v1:libraries-list")
    response = api_client.get(url)

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["uuid"] == str(library.uuid)


def test_library_list_excludes_channel_library(factories, logged_in_api_client):
    actor = logged_in_api_client.user.create_actor()
    factories["audio.Channel"](attributed_to=actor)
    url = reverse("api:v1:libraries-list")
    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert response.data["count"] == 0


def test_user_cannot_delete_other_actors_library(factories, logged_in_api_client):
    logged_in_api_client.user.create_actor()
    library = factories["music.Library"](privacy_level="everyone")

    url = reverse("api:v1:libraries-detail", kwargs={"uuid": library.uuid})
    response = logged_in_api_client.delete(url)

    assert response.status_code == 404


def test_library_delete_via_api_triggers_outbox(factories, mocker):
    dispatch = mocker.patch("funkwhale_api.federation.routes.outbox.dispatch")
    library = factories["music.Library"]()
    view = views.LibraryViewSet()
    view.perform_destroy(library)
    dispatch.assert_called_once_with(
        {"type": "Delete", "object": {"type": "Library"}}, context={"library": library}
    )


def test_user_cannot_get_other_not_playable_uploads(factories, logged_in_api_client):
    logged_in_api_client.user.create_actor()
    upload = factories["music.Upload"](
        import_status="finished", library__privacy_level="private"
    )

    url = reverse("api:v1:uploads-detail", kwargs={"uuid": upload.uuid})
    response = logged_in_api_client.get(url)

    assert response.status_code == 404


def test_user_can_get_retrieve_playable_uploads(factories, logged_in_api_client):
    logged_in_api_client.user.create_actor()
    upload = factories["music.Upload"](
        import_status="finished", library__privacy_level="everyone"
    )

    url = reverse("api:v1:uploads-detail", kwargs={"uuid": upload.uuid})
    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert response.data["uuid"] == str(upload.uuid)


def test_user_cannot_delete_other_actors_uploads(factories, logged_in_api_client):
    logged_in_api_client.user.create_actor()
    upload = factories["music.Upload"]()

    url = reverse("api:v1:uploads-detail", kwargs={"uuid": upload.uuid})
    response = logged_in_api_client.delete(url)

    assert response.status_code == 404


def test_upload_delete_via_api_triggers_outbox(factories, mocker):
    dispatch = mocker.patch("funkwhale_api.federation.routes.outbox.dispatch")
    upload = factories["music.Upload"]()
    view = views.UploadViewSet()
    view.perform_destroy(upload)
    dispatch.assert_called_once_with(
        {"type": "Delete", "object": {"type": "Audio"}}, context={"uploads": [upload]}
    )


def test_user_cannot_list_other_actors_uploads(factories, logged_in_api_client):
    logged_in_api_client.user.create_actor()
    factories["music.Upload"]()

    url = reverse("api:v1:uploads-list")
    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert response.data["count"] == 0


def test_user_can_create_upload(logged_in_api_client, factories, mocker, audio_file):
    library = factories["music.Library"](actor__user=logged_in_api_client.user)
    url = reverse("api:v1:uploads-list")
    m = mocker.patch("funkwhale_api.common.utils.on_commit")

    response = logged_in_api_client.post(
        url,
        {
            "audio_file": audio_file,
            "source": "upload://test",
            "import_reference": "test",
            "library": library.uuid,
            "import_metadata": '{"title": "foo"}',
        },
    )

    assert response.status_code == 201

    upload = library.uploads.latest("id")

    audio_file.seek(0)
    assert upload.audio_file.read() == audio_file.read()
    assert upload.source == "upload://test"
    assert upload.import_reference == "test"
    assert upload.import_status == "pending"
    assert upload.import_metadata == {"title": "foo"}
    assert upload.track is None
    m.assert_called_once_with(tasks.process_upload.delay, upload_id=upload.pk)


def test_user_can_create_upload_in_channel(
    logged_in_api_client, factories, mocker, audio_file
):
    actor = logged_in_api_client.user.create_actor()
    channel = factories["audio.Channel"](attributed_to=actor)
    url = reverse("api:v1:uploads-list")
    m = mocker.patch("funkwhale_api.common.utils.on_commit")
    album = factories["music.Album"](artist=channel.artist)
    response = logged_in_api_client.post(
        url,
        {
            "audio_file": audio_file,
            "source": "upload://test",
            "import_reference": "test",
            "channel": channel.uuid,
            "import_metadata": '{"title": "foo", "album": ' + str(album.pk) + "}",
        },
    )

    assert response.status_code == 201

    upload = channel.library.uploads.latest("id")

    assert upload.source == "upload://test"
    assert upload.import_reference == "test"
    assert upload.import_status == "pending"
    assert upload.import_metadata == {"title": "foo", "album": album.pk}
    assert upload.track is None
    m.assert_called_once_with(tasks.process_upload.delay, upload_id=upload.pk)


def test_user_can_create_draft_upload(
    logged_in_api_client, factories, mocker, audio_file
):
    library = factories["music.Library"](actor__user=logged_in_api_client.user)
    url = reverse("api:v1:uploads-list")
    m = mocker.patch("funkwhale_api.common.utils.on_commit")

    response = logged_in_api_client.post(
        url,
        {
            "audio_file": audio_file,
            "source": "upload://test",
            "import_reference": "test",
            "import_status": "draft",
            "library": library.uuid,
        },
    )

    assert response.status_code == 201

    upload = library.uploads.latest("id")

    audio_file.seek(0)
    assert upload.audio_file.read() == audio_file.read()
    assert upload.source == "upload://test"
    assert upload.import_reference == "test"
    assert upload.import_status == "draft"
    assert upload.mimetype == "audio/ogg"
    assert upload.track is None
    m.assert_not_called()


def test_user_can_patch_draft_upload(
    logged_in_api_client, factories, mocker, audio_file
):
    actor = logged_in_api_client.user.create_actor()
    library = factories["music.Library"](actor=actor)
    upload = factories["music.Upload"](library__actor=actor, import_status="draft")
    url = reverse("api:v1:uploads-detail", kwargs={"uuid": upload.uuid})
    m = mocker.patch("funkwhale_api.common.utils.on_commit")

    response = logged_in_api_client.patch(
        url,
        {
            "audio_file": audio_file,
            "source": "upload://test",
            "import_reference": "test",
            "library": library.uuid,
        },
    )

    assert response.status_code == 200

    upload.refresh_from_db()

    audio_file.seek(0)
    assert upload.audio_file.read() == audio_file.read()
    assert upload.source == "upload://test"
    assert upload.import_reference == "test"
    assert upload.import_status == "draft"
    assert upload.library == library
    m.assert_not_called()


@pytest.mark.parametrize("import_status", ["pending", "errored", "skipped", "finished"])
def test_user_cannot_patch_non_draft_upload(
    import_status, logged_in_api_client, factories
):
    actor = logged_in_api_client.user.create_actor()
    upload = factories["music.Upload"](
        library__actor=actor, import_status=import_status
    )
    url = reverse("api:v1:uploads-detail", kwargs={"uuid": upload.uuid})
    response = logged_in_api_client.patch(url, {"import_reference": "test"})

    assert response.status_code == 404


def test_user_can_patch_draft_upload_status_triggers_processing(
    logged_in_api_client, factories, mocker
):
    actor = logged_in_api_client.user.create_actor()
    upload = factories["music.Upload"](library__actor=actor, import_status="draft")
    url = reverse("api:v1:uploads-detail", kwargs={"uuid": upload.uuid})
    m = mocker.patch("funkwhale_api.common.utils.on_commit")

    response = logged_in_api_client.patch(url, {"import_status": "pending"})

    upload.refresh_from_db()

    assert response.status_code == 200
    assert upload.import_status == "pending"
    m.assert_called_once_with(tasks.process_upload.delay, upload_id=upload.pk)


def test_user_can_list_own_library_follows(factories, logged_in_api_client):
    actor = logged_in_api_client.user.create_actor()
    library = factories["music.Library"](actor=actor)
    another_library = factories["music.Library"](actor=actor)
    follow = factories["federation.LibraryFollow"](target=library)
    factories["federation.LibraryFollow"](target=another_library)

    url = reverse("api:v1:libraries-follows", kwargs={"uuid": library.uuid})

    response = logged_in_api_client.get(url)

    assert response.data == {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [federation_api_serializers.LibraryFollowSerializer(follow).data],
    }


@pytest.mark.parametrize("entity", ["artist", "album", "track"])
def test_can_get_libraries_for_music_entities(
    factories, api_client, entity, preferences
):
    preferences["common__api_authentication_required"] = False
    upload = factories["music.Upload"](playable=True)
    # another private library that should not appear
    factories["music.Upload"](
        import_status="finished", library__privacy_level="me", track=upload.track
    ).library
    library = upload.library
    setattr(library, "_uploads_count", 1)
    data = {
        "artist": upload.track.artist,
        "album": upload.track.album,
        "track": upload.track,
    }
    # libraries in channel should be missing excluded
    channel = factories["audio.Channel"](artist=upload.track.artist)
    factories["music.Upload"](
        library=channel.library, playable=True, track=upload.track
    )

    url = reverse("api:v1:{}s-libraries".format(entity), kwargs={"pk": data[entity].pk})

    response = api_client.get(url)
    expected = federation_api_serializers.LibrarySerializer(library).data

    assert response.status_code == 200
    assert response.data == {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [expected],
    }


def test_list_licenses(api_client, preferences, mocker):
    licenses.load(licenses.LICENSES)
    load = mocker.spy(licenses, "load")
    preferences["common__api_authentication_required"] = False

    expected = [
        serializers.LicenseSerializer(l.conf).data
        for l in models.License.objects.order_by("code")
    ]
    url = reverse("api:v1:licenses-list")

    response = api_client.get(url)

    assert response.data["results"] == expected
    load.assert_called_once_with(licenses.LICENSES)


def test_detail_license(api_client, preferences):
    preferences["common__api_authentication_required"] = False
    id = "cc-by-sa-4.0"
    expected = serializers.LicenseSerializer(licenses.LICENSES_BY_ID[id]).data

    url = reverse("api:v1:licenses-detail", kwargs={"pk": id})

    response = api_client.get(url)

    assert response.data == expected


def test_oembed_track(factories, no_api_auth, api_client, settings):
    settings.FUNKWHALE_URL = "http://test"
    settings.FUNKWHALE_EMBED_URL = "http://embed"
    track = factories["music.Track"](album__with_cover=True)
    url = reverse("api:v1:oembed")
    track_url = "https://test.com/library/tracks/{}".format(track.pk)
    iframe_src = "http://embed?type=track&id={}".format(track.pk)
    expected = {
        "version": "1.0",
        "type": "rich",
        "provider_name": settings.APP_NAME,
        "provider_url": settings.FUNKWHALE_URL,
        "height": 150,
        "width": 600,
        "title": "{} by {}".format(track.title, track.artist.name),
        "description": track.full_name,
        "thumbnail_url": federation_utils.full_url(
            track.album.attachment_cover.file.crop["200x200"].url
        ),
        "thumbnail_height": 200,
        "thumbnail_width": 200,
        "html": '<iframe width="600" height="150" scrolling="no" frameborder="no" src="{}"></iframe>'.format(
            iframe_src
        ),
        "author_name": track.artist.name,
        "author_url": federation_utils.full_url(
            utils.spa_reverse("library_artist", kwargs={"pk": track.artist.pk})
        ),
    }

    response = api_client.get(url, {"url": track_url, "format": "json"})

    assert response.data == expected


def test_oembed_album(factories, no_api_auth, api_client, settings):
    settings.FUNKWHALE_URL = "http://test"
    settings.FUNKWHALE_EMBED_URL = "http://embed"
    track = factories["music.Track"](album__with_cover=True)
    album = track.album
    url = reverse("api:v1:oembed")
    album_url = "https://test.com/library/albums/{}".format(album.pk)
    iframe_src = "http://embed?type=album&id={}".format(album.pk)
    expected = {
        "version": "1.0",
        "type": "rich",
        "provider_name": settings.APP_NAME,
        "provider_url": settings.FUNKWHALE_URL,
        "height": 400,
        "width": 600,
        "title": "{} by {}".format(album.title, album.artist.name),
        "description": "{} by {}".format(album.title, album.artist.name),
        "thumbnail_url": federation_utils.full_url(
            album.attachment_cover.file.crop["200x200"].url
        ),
        "thumbnail_height": 200,
        "thumbnail_width": 200,
        "html": '<iframe width="600" height="400" scrolling="no" frameborder="no" src="{}"></iframe>'.format(
            iframe_src
        ),
        "author_name": album.artist.name,
        "author_url": federation_utils.full_url(
            utils.spa_reverse("library_artist", kwargs={"pk": album.artist.pk})
        ),
    }

    response = api_client.get(url, {"url": album_url, "format": "json"})

    assert response.data == expected


def test_oembed_artist(factories, no_api_auth, api_client, settings):
    settings.FUNKWHALE_URL = "http://test"
    settings.FUNKWHALE_EMBED_URL = "http://embed"
    track = factories["music.Track"](album__with_cover=True)
    album = track.album
    artist = track.artist
    url = reverse("api:v1:oembed")
    artist_url = "https://test.com/library/artists/{}".format(artist.pk)
    iframe_src = "http://embed?type=artist&id={}".format(artist.pk)
    expected = {
        "version": "1.0",
        "type": "rich",
        "provider_name": settings.APP_NAME,
        "provider_url": settings.FUNKWHALE_URL,
        "height": 400,
        "width": 600,
        "title": artist.name,
        "description": artist.name,
        "thumbnail_url": federation_utils.full_url(
            album.attachment_cover.file.crop["200x200"].url
        ),
        "thumbnail_height": 200,
        "thumbnail_width": 200,
        "html": '<iframe width="600" height="400" scrolling="no" frameborder="no" src="{}"></iframe>'.format(
            iframe_src
        ),
        "author_name": artist.name,
        "author_url": federation_utils.full_url(
            utils.spa_reverse("library_artist", kwargs={"pk": artist.pk})
        ),
    }

    response = api_client.get(url, {"url": artist_url, "format": "json"})

    assert response.data == expected


def test_oembed_playlist(factories, no_api_auth, api_client, settings):
    settings.FUNKWHALE_URL = "http://test"
    settings.FUNKWHALE_EMBED_URL = "http://embed"
    playlist = factories["playlists.Playlist"](privacy_level="everyone")
    track = factories["music.Upload"](
        playable=True, track__album__with_cover=True
    ).track
    playlist.insert_many([track])
    url = reverse("api:v1:oembed")
    playlist_url = "https://test.com/library/playlists/{}".format(playlist.pk)
    iframe_src = "http://embed?type=playlist&id={}".format(playlist.pk)
    expected = {
        "version": "1.0",
        "type": "rich",
        "provider_name": settings.APP_NAME,
        "provider_url": settings.FUNKWHALE_URL,
        "height": 400,
        "width": 600,
        "title": playlist.name,
        "description": playlist.name,
        "thumbnail_url": federation_utils.full_url(
            track.album.attachment_cover.file.crop["200x200"].url
        ),
        "thumbnail_height": 200,
        "thumbnail_width": 200,
        "html": '<iframe width="600" height="400" scrolling="no" frameborder="no" src="{}"></iframe>'.format(
            iframe_src
        ),
        "author_name": playlist.name,
        "author_url": federation_utils.full_url(
            utils.spa_reverse("library_playlist", kwargs={"pk": playlist.pk})
        ),
    }

    response = api_client.get(url, {"url": playlist_url, "format": "json"})

    assert response.data == expected


@pytest.mark.parametrize(
    "factory_name, url_name",
    [
        ("music.Artist", "api:v1:artists-detail"),
        ("music.Album", "api:v1:albums-detail"),
        ("music.Track", "api:v1:tracks-detail"),
    ],
)
def test_refresh_remote_entity_when_param_is_true(
    factories,
    factory_name,
    url_name,
    mocker,
    logged_in_api_client,
    queryset_equal_queries,
):
    obj = factories[factory_name](mbid=None)

    assert obj.is_local is False

    new_mbid = uuid.uuid4()

    def fake_refetch(obj, queryset):
        obj.mbid = new_mbid
        return obj

    refetch_obj = mocker.patch.object(views, "refetch_obj", side_effect=fake_refetch)
    url = reverse(url_name, kwargs={"pk": obj.pk})
    response = logged_in_api_client.get(url, {"refresh": "true"})

    assert response.status_code == 200
    assert response.data["mbid"] == str(new_mbid)
    assert refetch_obj.call_count == 1
    assert refetch_obj.call_args[0][0] == obj


@pytest.mark.parametrize("param", ["false", "0", ""])
def test_refresh_remote_entity_no_param(
    factories, param, mocker, logged_in_api_client, service_actor
):
    obj = factories["music.Artist"](mbid=None)

    assert obj.is_local is False

    fetch_task = mocker.patch.object(federation_tasks, "fetch")
    url = reverse("api:v1:artists-detail", kwargs={"pk": obj.pk})
    response = logged_in_api_client.get(url, {"refresh": param})

    assert response.status_code == 200
    fetch_task.assert_not_called()
    assert service_actor.fetches.count() == 0


def test_refetch_obj_not_local(mocker, factories, service_actor):
    obj = factories["music.Artist"](local=True)
    fetch_task = mocker.patch.object(federation_tasks, "fetch")
    assert views.refetch_obj(obj, obj.__class__.objects.all()) == obj
    fetch_task.assert_not_called()
    assert service_actor.fetches.count() == 0


def test_refetch_obj_last_fetch_date_too_close(
    mocker, factories, settings, service_actor
):
    settings.FEDERATION_OBJECT_FETCH_DELAY = 300
    obj = factories["music.Artist"]()
    factories["federation.Fetch"](
        object=obj,
        creation_date=timezone.now()
        - datetime.timedelta(minutes=settings.FEDERATION_OBJECT_FETCH_DELAY - 1),
    )
    fetch_task = mocker.patch.object(federation_tasks, "fetch")
    assert views.refetch_obj(obj, obj.__class__.objects.all()) == obj
    fetch_task.assert_not_called()
    assert service_actor.fetches.count() == 0


def test_refetch_obj(mocker, factories, settings, service_actor):
    settings.FEDERATION_OBJECT_FETCH_DELAY = 300
    obj = factories["music.Artist"]()
    factories["federation.Fetch"](
        object=obj,
        creation_date=timezone.now()
        - datetime.timedelta(minutes=settings.FEDERATION_OBJECT_FETCH_DELAY + 1),
    )
    fetch_task = mocker.patch.object(federation_tasks, "fetch")
    views.refetch_obj(obj, obj.__class__.objects.all())
    fetch = obj.fetches.filter(actor=service_actor).order_by("-creation_date").first()
    fetch_task.assert_called_once_with(fetch_id=fetch.pk)


@pytest.mark.parametrize(
    "params, expected",
    [({}, 0), ({"include_channels": "false"}, 0), ({"include_channels": "true"}, 1)],
)
def test_artist_list_exclude_channels(
    params, expected, factories, logged_in_api_client
):
    factories["audio.Channel"]()

    url = reverse("api:v1:artists-list")
    response = logged_in_api_client.get(url, params)

    assert response.status_code == 200
    assert response.data["count"] == expected


@pytest.mark.parametrize(
    "params, expected",
    [({}, 0), ({"include_channels": "false"}, 0), ({"include_channels": "true"}, 1)],
)
def test_album_list_exclude_channels(params, expected, factories, logged_in_api_client):
    channel_artist = factories["audio.Channel"]().artist
    factories["music.Album"](artist=channel_artist)

    url = reverse("api:v1:albums-list")
    response = logged_in_api_client.get(url, params)

    assert response.status_code == 200
    assert response.data["count"] == expected


@pytest.mark.parametrize(
    "params, expected",
    [({}, 0), ({"include_channels": "false"}, 0), ({"include_channels": "true"}, 1)],
)
def test_track_list_exclude_channels(params, expected, factories, logged_in_api_client):
    channel_artist = factories["audio.Channel"]().artist
    factories["music.Track"](artist=channel_artist)

    url = reverse("api:v1:tracks-list")
    response = logged_in_api_client.get(url, params)

    assert response.status_code == 200
    assert response.data["count"] == expected


@pytest.mark.parametrize(
    "media_url, input, expected",
    [
        ("https://domain/media/", "https://domain/media/file.mp3", "/media/file.mp3"),
        (
            "https://domain/media/",
            "https://otherdomain/media/file.mp3",
            "https://otherdomain/media/file.mp3",
        ),
        ("https://domain/media/", "/media/file.mp3", "/media/file.mp3"),
    ],
)
def test_strip_absolute_media_url(media_url, input, expected, settings):
    settings.MEDIA_URL = media_url
    assert views.strip_absolute_media_url(input) == expected


def test_get_upload_audio_metadata(logged_in_api_client, factories):
    actor = logged_in_api_client.user.create_actor()
    upload = factories["music.Upload"](library__actor=actor)
    metadata = tasks.metadata.Metadata(upload.get_audio_file())
    serializer = tasks.metadata.TrackMetadataSerializer(data=metadata)
    url = reverse("api:v1:uploads-audio-file-metadata", kwargs={"uuid": upload.uuid})

    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert serializer.is_valid(raise_exception=True) is True
    assert response.data == serializer.validated_data


@pytest.mark.parametrize("use_fts", [True, False])
def test_search_get(use_fts, settings, logged_in_api_client, factories):
    settings.USE_FULL_TEXT_SEARCH = use_fts
    artist = factories["music.Artist"](name="Foo Fighters")
    album = factories["music.Album"](title="Foo Bar")
    track = factories["music.Track"](title="Foo Baz")
    tag = factories["tags.Tag"](name="Foo")

    factories["music.Track"]()
    factories["tags.Tag"]()

    url = reverse("api:v1:search")
    expected = {
        "artists": [serializers.ArtistWithAlbumsSerializer(artist).data],
        "albums": [serializers.AlbumSerializer(album).data],
        "tracks": [serializers.TrackSerializer(track).data],
        "tags": [views.TagSerializer(tag).data],
    }

    response = logged_in_api_client.get(url, {"q": "foo"})

    assert response.status_code == 200
    assert response.data == expected


def test_search_get_fts_advanced(settings, logged_in_api_client, factories):
    settings.USE_FULL_TEXT_SEARCH = True
    artist1 = factories["music.Artist"](name="Foo Bighters")
    artist2 = factories["music.Artist"](name="Bar Fighter")
    factories["music.Artist"]()

    url = reverse("api:v1:search")
    expected = {
        "artists": serializers.ArtistWithAlbumsSerializer(
            [artist2, artist1], many=True
        ).data,
        "albums": [],
        "tracks": [],
        "tags": [],
    }
    response = logged_in_api_client.get(url, {"q": '"foo | bar"'})

    assert response.status_code == 200
    assert response.data == expected


def test_search_get_fts_stop_words(settings, logged_in_api_client, factories):
    settings.USE_FULL_TEXT_SEARCH = True
    artist = factories["music.Artist"](name="she")
    factories["music.Artist"]()

    url = reverse("api:v1:search")
    expected = {
        "artists": [serializers.ArtistWithAlbumsSerializer(artist).data],
        "albums": [],
        "tracks": [],
        "tags": [],
    }
    response = logged_in_api_client.get(url, {"q": "sh"})

    assert response.status_code == 200
    assert response.data == expected


@pytest.mark.parametrize(
    "route, factory_name",
    [
        ("api:v1:artists-detail", "music.Artist"),
        ("api:v1:albums-detail", "music.Album"),
        ("api:v1:tracks-detail", "music.Track"),
    ],
)
def test_detail_includes_description_key(
    route, factory_name, logged_in_api_client, factories
):
    obj = factories[factory_name]()
    url = reverse(route, kwargs={"pk": obj.pk})

    response = logged_in_api_client.get(url)

    assert response.data["description"] is None


def test_channel_owner_can_create_album(factories, logged_in_api_client):
    actor = logged_in_api_client.user.create_actor()
    channel = factories["audio.Channel"](attributed_to=actor, artist__with_cover=True)
    attachment = factories["common.Attachment"](actor=actor)
    url = reverse("api:v1:albums-list")

    data = {
        "artist": channel.artist.pk,
        "cover": attachment.uuid,
        "title": "Hello world",
        "release_date": "2019-01-02",
        "tags": ["Hello", "World"],
        "description": {"content_type": "text/markdown", "text": "hello world"},
    }

    response = logged_in_api_client.post(url, data, format="json")

    assert response.status_code == 201

    album = channel.artist.albums.get(title=data["title"])

    assert (
        response.data
        == serializers.AlbumSerializer(album, context={"description": True}).data
    )
    assert album.attachment_cover == attachment
    assert album.attributed_to == actor
    assert album.release_date == datetime.date(2019, 1, 2)
    assert album.get_tags() == ["Hello", "World"]
    assert album.description.content_type == "text/markdown"
    assert album.description.text == "hello world"


def test_channel_owner_can_delete_album(factories, logged_in_api_client, mocker):
    dispatch = mocker.patch("funkwhale_api.federation.routes.outbox.dispatch")
    actor = logged_in_api_client.user.create_actor()
    channel = factories["audio.Channel"](attributed_to=actor)
    album = factories["music.Album"](artist=channel.artist)
    url = reverse("api:v1:albums-detail", kwargs={"pk": album.pk})

    response = logged_in_api_client.delete(url)

    assert response.status_code == 204

    dispatch.assert_called_once_with(
        {"type": "Delete", "object": {"type": "Album"}}, context={"album": album}
    )
    with pytest.raises(album.DoesNotExist):
        album.refresh_from_db()


def test_other_user_cannot_create_album(factories, logged_in_api_client):
    actor = logged_in_api_client.user.create_actor()
    channel = factories["audio.Channel"]()
    attachment = factories["common.Attachment"](actor=actor)
    url = reverse("api:v1:albums-list")

    data = {
        "artist": channel.artist.pk,
        "cover": attachment.uuid,
        "title": "Hello world",
        "release_date": "2019-01-02",
        "tags": ["Hello", "World"],
        "description": {"content_type": "text/markdown", "text": "hello world"},
    }

    response = logged_in_api_client.post(url, data, format="json")

    assert response.status_code == 400


def test_other_user_cannot_delete_album(factories, logged_in_api_client):
    logged_in_api_client.user.create_actor()
    channel = factories["audio.Channel"]()
    album = factories["music.Album"](artist=channel.artist)
    url = reverse("api:v1:albums-detail", kwargs={"pk": album.pk})

    response = logged_in_api_client.delete(url)

    assert response.status_code == 404
    album.refresh_from_db()


def test_channel_owner_can_delete_track(factories, logged_in_api_client, mocker):
    dispatch = mocker.patch("funkwhale_api.federation.routes.outbox.dispatch")
    actor = logged_in_api_client.user.create_actor()
    channel = factories["audio.Channel"](attributed_to=actor)
    track = factories["music.Track"](artist=channel.artist)
    upload1 = factories["music.Upload"](track=track)
    upload2 = factories["music.Upload"](track=track)
    url = reverse("api:v1:tracks-detail", kwargs={"pk": track.pk})

    response = logged_in_api_client.delete(url)

    assert response.status_code == 204
    dispatch.assert_called_once_with(
        {"type": "Delete", "object": {"type": "Audio"}},
        context={"uploads": [upload1, upload2]},
    )
    with pytest.raises(track.DoesNotExist):
        track.refresh_from_db()


def test_other_user_cannot_delete_track(factories, logged_in_api_client):
    logged_in_api_client.user.create_actor()
    channel = factories["audio.Channel"]()
    track = factories["music.Track"](artist=channel.artist)
    url = reverse("api:v1:tracks-detail", kwargs={"pk": track.pk})

    response = logged_in_api_client.delete(url)

    assert response.status_code == 404
    track.refresh_from_db()


def test_listen_to_track_with_scoped_token(factories, api_client):
    user = factories["users.User"]()
    token = users_authentication.generate_scoped_token(
        user_id=user.pk, user_secret=user.secret_key, scopes=["read:libraries"]
    )
    upload = factories["music.Upload"](playable=True)
    url = reverse("api:v1:listen-detail", kwargs={"uuid": upload.track.uuid})
    response = api_client.get(url, {"token": token})

    assert response.status_code == 200

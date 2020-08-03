import pytest
from django.core.paginator import Paginator
from django.urls import reverse

from funkwhale_api.common import utils

from funkwhale_api.federation import (
    actors,
    serializers,
    webfinger,
    utils as federation_utils,
)


def test_authenticate_skips_anonymous_fetch_when_allow_list_enabled(
    preferences, api_client
):
    preferences["moderation__allow_list_enabled"] = True
    actor = actors.get_service_actor()
    url = reverse(
        "federation:actors-detail",
        kwargs={"preferred_username": actor.preferred_username},
    )
    response = api_client.get(url)

    assert response.status_code == 403


def test_wellknown_webfinger_validates_resource(db, api_client, settings, mocker):
    clean = mocker.spy(webfinger, "clean_resource")
    url = reverse("federation:well-known-webfinger")
    response = api_client.get(url, data={"resource": "something"})

    clean.assert_called_once_with("something")
    assert url == "/.well-known/webfinger"
    assert response.status_code == 400
    assert response.data["errors"]["resource"] == ("Missing webfinger resource type")


def test_wellknown_nodeinfo(db, preferences, api_client, settings):
    expected = {
        "links": [
            {
                "rel": "http://nodeinfo.diaspora.software/ns/schema/2.0",
                "href": "{}{}".format(
                    settings.FUNKWHALE_URL, reverse("api:v1:instance:nodeinfo-2.0")
                ),
            }
        ]
    }
    url = reverse("federation:well-known-nodeinfo")
    response = api_client.get(url, HTTP_ACCEPT="application/jrd+json")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/jrd+json"
    assert response.data == expected


def test_local_actor_detail(factories, api_client):
    user = factories["users.User"](with_actor=True)
    url = reverse(
        "federation:actors-detail",
        kwargs={"preferred_username": user.actor.preferred_username},
    )
    serializer = serializers.ActorSerializer(user.actor)
    response = api_client.get(url)

    assert response.status_code == 200
    assert response.data == serializer.data


def test_service_actor_detail(factories, api_client):
    actor = actors.get_service_actor()
    url = reverse(
        "federation:actors-detail",
        kwargs={"preferred_username": actor.preferred_username},
    )
    serializer = serializers.ActorSerializer(actor)
    response = api_client.get(url)

    assert response.status_code == 200
    assert response.data == serializer.data


def test_local_actor_inbox_post_requires_auth(factories, api_client):
    user = factories["users.User"](with_actor=True)
    url = reverse(
        "federation:actors-inbox",
        kwargs={"preferred_username": user.actor.preferred_username},
    )
    response = api_client.post(url, {"hello": "world"})

    assert response.status_code == 403


def test_local_actor_inbox_post(factories, api_client, mocker, authenticated_actor):
    patched_receive = mocker.patch("funkwhale_api.federation.activity.receive")
    user = factories["users.User"](with_actor=True)
    url = reverse(
        "federation:actors-inbox",
        kwargs={"preferred_username": user.actor.preferred_username},
    )
    response = api_client.post(url, {"hello": "world"}, format="json")

    assert response.status_code == 200
    patched_receive.assert_called_once_with(
        activity={"hello": "world"},
        on_behalf_of=authenticated_actor,
        inbox_actor=user.actor,
    )


def test_local_actor_inbox_post_receive(
    factories, api_client, mocker, authenticated_actor
):
    payload = {
        "to": [
            "https://test.server/federation/music/libraries/956af6c9-1eb9-4117-8d17-b15e7b34afeb/followers"
        ],
        "type": "Create",
        "actor": authenticated_actor.fid,
        "object": {
            "id": "https://test.server/federation/music/uploads/fe564a47-b1d4-4596-bf96-008ccf407672",
            "type": "Audio",
        },
        "@context": [
            "https://www.w3.org/ns/activitystreams",
            "https://w3id.org/security/v1",
            {},
        ],
    }
    user = factories["users.User"](with_actor=True)
    url = reverse(
        "federation:actors-inbox",
        kwargs={"preferred_username": user.actor.preferred_username},
    )
    response = api_client.post(url, payload, format="json")

    assert response.status_code == 200


def test_shared_inbox_post(factories, api_client, mocker, authenticated_actor):
    patched_receive = mocker.patch("funkwhale_api.federation.activity.receive")
    url = reverse("federation:shared-inbox")
    response = api_client.post(url, {"hello": "world"}, format="json")

    assert response.status_code == 200
    patched_receive.assert_called_once_with(
        activity={"hello": "world"}, on_behalf_of=authenticated_actor
    )


def test_wellknown_webfinger_local(factories, api_client, settings, mocker):
    user = factories["users.User"](with_actor=True)
    url = reverse("federation:well-known-webfinger")
    response = api_client.get(
        url,
        data={"resource": "acct:{}".format(user.actor.webfinger_subject)},
        HTTP_ACCEPT="application/jrd+json",
    )
    serializer = serializers.ActorWebfingerSerializer(user.actor)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/jrd+json"
    assert response.data == serializer.data


@pytest.mark.parametrize("privacy_level", ["me", "instance", "everyone"])
def test_music_library_retrieve(factories, api_client, privacy_level):
    library = factories["music.Library"](privacy_level=privacy_level, actor__local=True)
    expected = serializers.LibrarySerializer(library).data

    url = reverse("federation:music:libraries-detail", kwargs={"uuid": library.uuid})
    response = api_client.get(url)

    assert response.status_code == 200
    assert response.data == expected


def test_music_library_retrieve_excludes_channel_libraries(factories, api_client):
    channel = factories["audio.Channel"](local=True)
    library = channel.library

    url = reverse("federation:music:libraries-detail", kwargs={"uuid": library.uuid})
    response = api_client.get(url)

    assert response.status_code == 404


def test_actor_retrieve_excludes_channel_with_private_library(factories, api_client):
    channel = factories["audio.Channel"](external=True, library__privacy_level="me")

    url = reverse(
        "federation:actors-detail",
        kwargs={"preferred_username": channel.actor.preferred_username},
    )
    response = api_client.get(url)

    assert response.status_code == 404


def test_music_library_retrieve_page_public(factories, api_client):
    library = factories["music.Library"](privacy_level="everyone", actor__local=True)
    upload = factories["music.Upload"](library=library, import_status="finished")
    id = library.get_federation_id()
    expected = serializers.CollectionPageSerializer(
        {
            "id": id,
            "item_serializer": serializers.UploadSerializer,
            "actor": library.actor,
            "page": Paginator([upload], 1).page(1),
            "name": library.name,
            "summary": library.description,
        }
    ).data

    url = reverse("federation:music:libraries-detail", kwargs={"uuid": library.uuid})
    response = api_client.get(url, {"page": 1})

    assert response.status_code == 200
    assert response.data == expected


def test_channel_outbox_retrieve(factories, api_client):
    channel = factories["audio.Channel"](actor__local=True)
    expected = serializers.ChannelOutboxSerializer(channel).data

    url = reverse(
        "federation:actors-outbox",
        kwargs={"preferred_username": channel.actor.preferred_username},
    )
    response = api_client.get(url)

    assert response.status_code == 200
    assert response.data == expected


def test_channel_outbox_retrieve_page(factories, api_client):
    channel = factories["audio.Channel"](actor__local=True)
    upload = factories["music.Upload"](library=channel.library, playable=True)
    url = reverse(
        "federation:actors-outbox",
        kwargs={"preferred_username": channel.actor.preferred_username},
    )

    expected = serializers.CollectionPageSerializer(
        {
            "id": channel.actor.outbox_url,
            "item_serializer": serializers.ChannelCreateUploadSerializer,
            "actor": channel.actor,
            "page": Paginator([upload], 1).page(1),
        }
    ).data

    response = api_client.get(url, {"page": 1})

    assert response.status_code == 200
    assert response.data == expected


def test_channel_upload_retrieve(factories, api_client):
    channel = factories["audio.Channel"](local=True)
    upload = factories["music.Upload"](library=channel.library, playable=True)
    url = reverse("federation:music:uploads-detail", kwargs={"uuid": upload.uuid})

    expected = serializers.ChannelUploadSerializer(upload).data

    response = api_client.get(url)

    assert response.status_code == 200
    assert response.data == expected


def test_channel_upload_retrieve_activity(factories, api_client):
    channel = factories["audio.Channel"](local=True)
    upload = factories["music.Upload"](library=channel.library, playable=True)
    url = reverse("federation:music:uploads-activity", kwargs={"uuid": upload.uuid})

    expected = serializers.ChannelCreateUploadSerializer(upload).data

    response = api_client.get(url)

    assert response.status_code == 200
    assert response.data == expected


@pytest.mark.parametrize("privacy_level", ["me", "instance"])
def test_music_library_retrieve_page_private(factories, api_client, privacy_level):
    library = factories["music.Library"](privacy_level=privacy_level, actor__local=True)
    url = reverse("federation:music:libraries-detail", kwargs={"uuid": library.uuid})
    response = api_client.get(url, {"page": 1})

    assert response.status_code == 403


@pytest.mark.parametrize("approved,expected", [(True, 200), (False, 403)])
def test_music_library_retrieve_page_follow(
    factories, api_client, authenticated_actor, approved, expected
):
    library = factories["music.Library"](privacy_level="me", actor__local=True)
    factories["federation.LibraryFollow"](
        actor=authenticated_actor, target=library, approved=approved
    )
    url = reverse("federation:music:libraries-detail", kwargs={"uuid": library.uuid})
    response = api_client.get(url, {"page": 1})

    assert response.status_code == expected


@pytest.mark.parametrize(
    "factory, serializer_class, namespace",
    [
        ("music.Artist", serializers.ArtistSerializer, "artists"),
        ("music.Album", serializers.AlbumSerializer, "albums"),
        ("music.Track", serializers.TrackSerializer, "tracks"),
    ],
)
def test_music_local_entity_detail(
    factories, api_client, factory, serializer_class, namespace, settings
):
    obj = factories[factory](fid="http://{}/1".format(settings.FEDERATION_HOSTNAME))
    url = reverse(
        "federation:music:{}-detail".format(namespace), kwargs={"uuid": obj.uuid}
    )
    response = api_client.get(url)

    assert response.status_code == 200
    assert response.data == serializer_class(obj).data


@pytest.mark.parametrize(
    "factory, namespace",
    [("music.Artist", "artists"), ("music.Album", "albums"), ("music.Track", "tracks")],
)
def test_music_non_local_entity_detail(
    factories, api_client, factory, namespace, settings
):
    obj = factories[factory](fid="http://wrong-domain/1")
    url = reverse(
        "federation:music:{}-detail".format(namespace), kwargs={"uuid": obj.uuid}
    )
    response = api_client.get(url)

    assert response.status_code == 404


@pytest.mark.parametrize(
    "privacy_level, expected", [("me", 404), ("instance", 404), ("everyone", 200)]
)
def test_music_upload_detail(factories, api_client, privacy_level, expected):
    upload = factories["music.Upload"](
        library__privacy_level=privacy_level,
        library__actor__local=True,
        import_status="finished",
    )
    url = reverse("federation:music:uploads-detail", kwargs={"uuid": upload.uuid})
    response = api_client.get(url)

    assert response.status_code == expected
    if expected == 200:
        assert response.data == serializers.UploadSerializer(upload).data


@pytest.mark.parametrize("privacy_level", ["me", "instance"])
def test_music_upload_detail_private_approved_follow(
    factories, api_client, authenticated_actor, privacy_level
):
    upload = factories["music.Upload"](
        library__privacy_level=privacy_level,
        library__actor__local=True,
        import_status="finished",
    )
    factories["federation.LibraryFollow"](
        actor=authenticated_actor, target=upload.library, approved=True
    )
    url = reverse("federation:music:uploads-detail", kwargs={"uuid": upload.uuid})
    response = api_client.get(url)

    assert response.status_code == 200


@pytest.mark.parametrize(
    "accept_header,default,expected",
    [
        ("text/html,application/xhtml+xml", True, True),
        ("text/html,application/json", True, True),
        ("", True, False),
        (None, True, False),
        ("application/json", True, False),
        ("application/activity+json", True, False),
        ("application/json,text/html", True, False),
        ("application/activity+json,text/html", True, False),
        ("unrelated/ct", True, True),
        ("unrelated/ct", False, False),
    ],
)
def test_should_redirect_ap_to_html(accept_header, default, expected):
    assert (
        federation_utils.should_redirect_ap_to_html(accept_header, default) is expected
    )


def test_music_library_retrieve_redirects_to_html_if_header_set(
    factories, api_client, settings
):
    library = factories["music.Library"](actor__local=True)

    url = reverse("federation:music:libraries-detail", kwargs={"uuid": library.uuid})
    response = api_client.get(url, HTTP_ACCEPT="text/html")
    expected_url = utils.join_url(
        settings.FUNKWHALE_URL,
        utils.spa_reverse("library_library", kwargs={"uuid": library.uuid}),
    )
    assert response.status_code == 302
    assert response["Location"] == expected_url


def test_actor_retrieve_redirects_to_html_if_header_set(
    factories, api_client, settings
):
    actor = factories["federation.Actor"](local=True)

    url = reverse(
        "federation:actors-detail",
        kwargs={"preferred_username": actor.preferred_username},
    )
    response = api_client.get(url, HTTP_ACCEPT="text/html")
    expected_url = utils.join_url(
        settings.FUNKWHALE_URL,
        utils.spa_reverse(
            "actor_detail", kwargs={"username": actor.preferred_username}
        ),
    )
    assert response.status_code == 302
    assert response["Location"] == expected_url


def test_channel_actor_retrieve_redirects_to_html_if_header_set(
    factories, api_client, settings
):
    channel = factories["audio.Channel"](local=True)

    url = reverse(
        "federation:actors-detail",
        kwargs={"preferred_username": channel.actor.preferred_username},
    )
    response = api_client.get(url, HTTP_ACCEPT="text/html")
    expected_url = utils.join_url(
        settings.FUNKWHALE_URL,
        utils.spa_reverse(
            "channel_detail", kwargs={"username": channel.actor.preferred_username}
        ),
    )
    assert response.status_code == 302
    assert response["Location"] == expected_url


def test_upload_retrieve_redirects_to_html_if_header_set(
    factories, api_client, settings
):
    upload = factories["music.Upload"](library__local=True, playable=True)

    url = reverse("federation:music:uploads-detail", kwargs={"uuid": upload.uuid},)
    response = api_client.get(url, HTTP_ACCEPT="text/html")
    expected_url = utils.join_url(
        settings.FUNKWHALE_URL,
        utils.spa_reverse("library_track", kwargs={"pk": upload.track.pk}),
    )
    assert response.status_code == 302
    assert response["Location"] == expected_url


def test_track_retrieve_redirects_to_html_if_header_set(
    factories, api_client, settings
):
    track = factories["music.Track"](local=True)

    url = reverse("federation:music:tracks-detail", kwargs={"uuid": track.uuid},)
    response = api_client.get(url, HTTP_ACCEPT="text/html")
    expected_url = utils.join_url(
        settings.FUNKWHALE_URL,
        utils.spa_reverse("library_track", kwargs={"pk": track.pk}),
    )
    assert response.status_code == 302
    assert response["Location"] == expected_url


def test_album_retrieve_redirects_to_html_if_header_set(
    factories, api_client, settings
):
    album = factories["music.Album"](local=True)

    url = reverse("federation:music:albums-detail", kwargs={"uuid": album.uuid},)
    response = api_client.get(url, HTTP_ACCEPT="text/html")
    expected_url = utils.join_url(
        settings.FUNKWHALE_URL,
        utils.spa_reverse("library_album", kwargs={"pk": album.pk}),
    )
    assert response.status_code == 302
    assert response["Location"] == expected_url


def test_artist_retrieve_redirects_to_html_if_header_set(
    factories, api_client, settings
):
    artist = factories["music.Artist"](local=True)

    url = reverse("federation:music:artists-detail", kwargs={"uuid": artist.uuid},)
    response = api_client.get(url, HTTP_ACCEPT="text/html")
    expected_url = utils.join_url(
        settings.FUNKWHALE_URL,
        utils.spa_reverse("library_artist", kwargs={"pk": artist.pk}),
    )
    assert response.status_code == 302
    assert response["Location"] == expected_url


@pytest.mark.parametrize("index", ["channels", "libraries"])
def test_public_index_disabled(index, api_client, preferences):
    preferences["federation__public_index"] = False
    url = reverse("federation:index:index-{}".format(index))
    response = api_client.get(url)

    assert response.status_code == 405


def test_index_channels_retrieve(factories, api_client):
    channels = [
        factories["audio.Channel"](actor__local=True),
        factories["audio.Channel"](actor__local=True),
        factories["audio.Channel"](actor__local=True),
    ]
    expected = serializers.IndexSerializer(
        {
            "id": federation_utils.full_url(reverse("federation:index:index-channels")),
            "items": channels[0].__class__.objects.order_by("creation_date"),
            "page_size": 100,
        },
    ).data

    url = reverse("federation:index:index-channels",)
    response = api_client.get(url)

    assert response.status_code == 200
    assert response.data == expected


def test_index_channels_page(factories, api_client, preferences):
    preferences["federation__collection_page_size"] = 1
    remote_actor = factories["federation.Actor"]()
    channels = [
        factories["audio.Channel"](actor__local=True),
        factories["audio.Channel"](actor__local=True),
        factories["audio.Channel"](actor__local=True),
        factories["audio.Channel"](actor=remote_actor),
    ]
    id = federation_utils.full_url(reverse("federation:index:index-channels"))
    expected = serializers.CollectionPageSerializer(
        {
            "id": id,
            "item_serializer": serializers.ActorSerializer,
            "page": Paginator([c.actor for c in channels][:3], 1).page(1),
            "actor": None,
        }
    ).data

    url = reverse("federation:index:index-channels")
    response = api_client.get(url, {"page": 1})

    assert response.status_code == 200
    assert response.data == expected


def test_index_libraries_retrieve(factories, api_client):
    remote_actor = factories["federation.Actor"]()
    libraries = [
        factories["music.Library"](actor__local=True, privacy_level="everyone"),
        factories["music.Library"](actor__local=True, privacy_level="everyone"),
        factories["music.Library"](actor__local=True, privacy_level="me"),
        factories["music.Library"](actor=remote_actor, privacy_level="everyone"),
    ]
    expected = serializers.IndexSerializer(
        {
            "id": federation_utils.full_url(
                reverse("federation:index:index-libraries")
            ),
            "items": libraries[0]
            .__class__.objects.local()
            .filter(privacy_level="everyone")
            .order_by("creation_date"),
            "page_size": 100,
        },
    ).data

    url = reverse("federation:index:index-libraries")
    response = api_client.get(url)

    assert response.status_code == 200
    assert response.data == expected


def test_index_libraries_page(factories, api_client, preferences):
    preferences["federation__collection_page_size"] = 1
    remote_actor = factories["federation.Actor"]()
    libraries = [
        factories["music.Library"](actor__local=True, privacy_level="everyone"),
        factories["music.Library"](actor__local=True, privacy_level="everyone"),
        factories["music.Library"](actor__local=True, privacy_level="me"),
        factories["music.Library"](actor=remote_actor, privacy_level="everyone"),
    ]
    id = federation_utils.full_url(reverse("federation:index:index-libraries"))
    expected = serializers.CollectionPageSerializer(
        {
            "id": id,
            "item_serializer": serializers.LibrarySerializer,
            "page": Paginator(libraries[:2], 1).page(1),
            "actor": None,
        }
    ).data

    url = reverse("federation:index:index-libraries")
    response = api_client.get(url, {"page": 1})

    assert response.status_code == 200
    assert response.data == expected

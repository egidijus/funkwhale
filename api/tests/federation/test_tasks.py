import datetime
import os
import pathlib
import pytest

from django.utils import timezone

from funkwhale_api.federation import jsonld
from funkwhale_api.federation import models
from funkwhale_api.federation import serializers
from funkwhale_api.federation import tasks
from funkwhale_api.federation import utils


def test_clean_federation_music_cache_if_no_listen(preferences, factories):
    preferences["federation__music_cache_duration"] = 60
    remote_library = factories["music.Library"]()
    upload1 = factories["music.Upload"](
        library=remote_library,
        accessed_date=timezone.now(),
        source="https://upload1.mp3",
    )
    upload2 = factories["music.Upload"](
        library=remote_library,
        accessed_date=timezone.now() - datetime.timedelta(minutes=61),
        source="https://upload2.mp3",
    )
    upload3 = factories["music.Upload"](
        library=remote_library, accessed_date=None, source="http://upload3.mp3"
    )
    # local upload, should not be cleaned
    upload4 = factories["music.Upload"](library__actor__local=True, accessed_date=None)
    # non-http source , not cleaned
    upload5 = factories["music.Upload"](accessed_date=None, source="noop")

    path1 = upload1.audio_file_path
    path2 = upload2.audio_file_path
    path3 = upload3.audio_file_path
    path4 = upload4.audio_file_path
    path5 = upload5.audio_file_path

    tasks.clean_music_cache()

    upload1.refresh_from_db()
    upload2.refresh_from_db()
    upload3.refresh_from_db()
    upload4.refresh_from_db()
    upload5.refresh_from_db()

    assert bool(upload1.audio_file) is True
    assert bool(upload2.audio_file) is False
    assert bool(upload3.audio_file) is False
    assert bool(upload4.audio_file) is True
    assert bool(upload5.audio_file) is True
    assert os.path.exists(path1) is True
    assert os.path.exists(path2) is False
    assert os.path.exists(path3) is False
    assert os.path.exists(path4) is True
    assert os.path.exists(path5) is True


def test_clean_federation_music_cache_orphaned(settings, preferences, factories):
    preferences["federation__music_cache_duration"] = 60
    path = os.path.join(settings.MEDIA_ROOT, "federation_cache", "tracks")
    keep_path = os.path.join(os.path.join(path, "1a", "b2"), "keep.ogg")
    remove_path = os.path.join(os.path.join(path, "c3", "d4"), "remove.ogg")
    os.makedirs(os.path.dirname(keep_path), exist_ok=True)
    os.makedirs(os.path.dirname(remove_path), exist_ok=True)
    pathlib.Path(keep_path).touch()
    pathlib.Path(remove_path).touch()
    upload = factories["music.Upload"](
        accessed_date=timezone.now(), audio_file__path=keep_path
    )

    tasks.clean_music_cache()

    upload.refresh_from_db()

    assert bool(upload.audio_file) is True
    assert os.path.exists(upload.audio_file_path) is True
    assert os.path.exists(remove_path) is False


def test_handle_in(factories, mocker, now, queryset_equal_list):
    mocked_dispatch = mocker.patch("funkwhale_api.federation.routes.inbox.dispatch")

    r1 = factories["users.User"](with_actor=True).actor
    r2 = factories["users.User"](with_actor=True).actor
    a = factories["federation.Activity"](payload={"hello": "world"})
    ii1 = factories["federation.InboxItem"](activity=a, actor=r1)
    ii2 = factories["federation.InboxItem"](activity=a, actor=r2)
    tasks.dispatch_inbox(activity_id=a.pk, call_handlers=False)

    mocked_dispatch.assert_called_once_with(
        a.payload,
        context={"actor": a.actor, "activity": a, "inbox_items": [ii1, ii2]},
        call_handlers=False,
    )


@pytest.mark.parametrize(
    "type, call_handlers", [("Noop", False), ("Update", False), ("Follow", True)]
)
def test_dispatch_outbox(factories, mocker, type, call_handlers):
    mocked_inbox = mocker.patch("funkwhale_api.federation.tasks.dispatch_inbox.delay")
    mocked_deliver_to_remote = mocker.patch(
        "funkwhale_api.federation.tasks.deliver_to_remote.delay"
    )
    activity = factories["federation.Activity"](actor__local=True, type=type)
    factories["federation.InboxItem"](activity=activity)
    delivery = factories["federation.Delivery"](activity=activity)
    tasks.dispatch_outbox(activity_id=activity.pk)
    mocked_inbox.assert_called_once_with(
        activity_id=activity.pk, call_handlers=call_handlers
    )
    mocked_deliver_to_remote.assert_called_once_with(delivery_id=delivery.pk)


def test_dispatch_outbox_disabled_federation(factories, mocker, preferences):
    preferences["federation__enabled"] = False
    mocked_inbox = mocker.patch("funkwhale_api.federation.tasks.dispatch_inbox.delay")
    mocked_deliver_to_remote = mocker.patch(
        "funkwhale_api.federation.tasks.deliver_to_remote.delay"
    )
    activity = factories["federation.Activity"](actor__local=True)
    factories["federation.InboxItem"](activity=activity)
    factories["federation.Delivery"](activity=activity)
    tasks.dispatch_outbox(activity_id=activity.pk)
    mocked_inbox.assert_called_once_with(activity_id=activity.pk, call_handlers=False)
    mocked_deliver_to_remote.assert_not_called()


def test_deliver_to_remote_success_mark_as_delivered(factories, r_mock, now):
    delivery = factories["federation.Delivery"]()
    r_mock.post(delivery.inbox_url)
    tasks.deliver_to_remote(delivery_id=delivery.pk)

    delivery.refresh_from_db()

    request = r_mock.request_history[0]
    assert delivery.is_delivered is True
    assert delivery.attempts == 1
    assert delivery.last_attempt_date == now
    assert r_mock.called is True
    assert r_mock.call_count == 1
    assert request.url == delivery.inbox_url
    assert request.headers["content-type"] == "application/activity+json"
    assert request.json() == delivery.activity.payload


def test_deliver_to_remote_error(factories, r_mock, now):
    delivery = factories["federation.Delivery"]()
    r_mock.post(delivery.inbox_url, status_code=404)

    with pytest.raises(tasks.RequestException):
        tasks.deliver_to_remote(delivery_id=delivery.pk)

    delivery.refresh_from_db()

    assert delivery.is_delivered is False
    assert delivery.attempts == 1
    assert delivery.last_attempt_date == now


def test_fetch_nodeinfo(factories, r_mock, now):
    wellknown_url = "https://test.test/.well-known/nodeinfo"
    nodeinfo_url = "https://test.test/nodeinfo"

    r_mock.get(
        wellknown_url,
        json={
            "links": [
                {
                    "rel": "http://nodeinfo.diaspora.software/ns/schema/2.0",
                    "href": "https://test.test/nodeinfo",
                }
            ]
        },
    )
    r_mock.get(nodeinfo_url, json={"hello": "world"})

    assert tasks.fetch_nodeinfo("test.test") == {"hello": "world"}


def test_update_domain_nodeinfo(factories, mocker, now, service_actor):
    domain = factories["federation.Domain"](nodeinfo_fetch_date=None)
    actor = factories["federation.Actor"](fid="https://actor.id")
    retrieve_ap_object = mocker.spy(utils, "retrieve_ap_object")

    mocker.patch.object(
        tasks,
        "fetch_nodeinfo",
        return_value={"hello": "world", "metadata": {"actorId": "https://actor.id"}},
    )

    assert domain.nodeinfo == {}
    assert domain.nodeinfo_fetch_date is None
    assert domain.service_actor is None

    tasks.update_domain_nodeinfo(domain_name=domain.name)

    domain.refresh_from_db()

    assert domain.nodeinfo_fetch_date == now
    assert domain.nodeinfo == {
        "status": "ok",
        "payload": {"hello": "world", "metadata": {"actorId": "https://actor.id"}},
    }
    assert domain.service_actor == actor

    retrieve_ap_object.assert_called_once_with(
        "https://actor.id",
        actor=service_actor,
        queryset=models.Actor,
        serializer_class=serializers.ActorSerializer,
    )


def test_update_domain_nodeinfo_error(factories, r_mock, now):
    domain = factories["federation.Domain"](nodeinfo_fetch_date=None)
    wellknown_url = "https://{}/.well-known/nodeinfo".format(domain.name)

    r_mock.get(wellknown_url, status_code=500)

    tasks.update_domain_nodeinfo(domain_name=domain.name)

    domain.refresh_from_db()

    assert domain.nodeinfo_fetch_date == now
    assert domain.nodeinfo == {
        "status": "error",
        "error": "500 Server Error: None for url: {}".format(wellknown_url),
    }


def test_refresh_nodeinfo_known_nodes(settings, factories, mocker, now):
    settings.NODEINFO_REFRESH_DELAY = 666

    refreshed = [
        factories["federation.Domain"](nodeinfo_fetch_date=None),
        factories["federation.Domain"](
            nodeinfo_fetch_date=now
            - datetime.timedelta(seconds=settings.NODEINFO_REFRESH_DELAY + 1)
        ),
    ]
    factories["federation.Domain"](
        nodeinfo_fetch_date=now
        - datetime.timedelta(seconds=settings.NODEINFO_REFRESH_DELAY - 1)
    )

    update_domain_nodeinfo = mocker.patch.object(tasks.update_domain_nodeinfo, "delay")

    tasks.refresh_nodeinfo_known_nodes()

    assert update_domain_nodeinfo.call_count == len(refreshed)

    for d in refreshed:
        update_domain_nodeinfo.assert_any_call(domain_name=d.name)


def test_handle_purge_actors(factories, mocker):
    to_purge = factories["federation.Actor"]()
    keeped = [
        factories["music.Upload"](),
        factories["federation.Activity"](),
        factories["federation.InboxItem"](),
        factories["federation.Follow"](),
        factories["federation.LibraryFollow"](),
    ]

    library = factories["music.Library"](actor=to_purge)
    deleted = [
        library,
        factories["music.Upload"](library=library),
        factories["federation.Activity"](actor=to_purge),
        factories["federation.InboxItem"](actor=to_purge),
        factories["federation.Follow"](actor=to_purge),
        factories["federation.LibraryFollow"](actor=to_purge),
    ]

    tasks.handle_purge_actors([to_purge.pk])

    for k in keeped:
        # this should not be deleted
        k.refresh_from_db()

    for d in deleted:
        with pytest.raises(d.__class__.DoesNotExist):
            d.refresh_from_db()


def test_handle_purge_actors_restrict_media(factories, mocker):
    to_purge = factories["federation.Actor"]()
    keeped = [
        factories["music.Upload"](),
        factories["federation.Activity"](),
        factories["federation.InboxItem"](),
        factories["federation.Follow"](),
        factories["federation.LibraryFollow"](),
        factories["federation.Activity"](actor=to_purge),
        factories["federation.InboxItem"](actor=to_purge),
        factories["federation.Follow"](actor=to_purge),
    ]

    library = factories["music.Library"](actor=to_purge)
    deleted = [
        library,
        factories["music.Upload"](library=library),
        factories["federation.LibraryFollow"](actor=to_purge),
    ]

    tasks.handle_purge_actors([to_purge.pk], only=["media"])

    for k in keeped:
        # this should not be deleted
        k.refresh_from_db()

    for d in deleted:
        with pytest.raises(d.__class__.DoesNotExist):
            d.refresh_from_db()


def test_purge_actors(factories, mocker):
    handle_purge_actors = mocker.spy(tasks, "handle_purge_actors")
    factories["federation.Actor"]()
    to_delete = factories["federation.Actor"]()
    to_delete_domain = factories["federation.Actor"]()
    tasks.purge_actors(
        ids=[to_delete.pk], domains=[to_delete_domain.domain.name], only=["hello"]
    )

    handle_purge_actors.assert_called_once_with(
        ids=[to_delete.pk, to_delete_domain.pk], only=["hello"]
    )


def test_rotate_actor_key(factories, settings, mocker):
    actor = factories["federation.Actor"](local=True)
    get_key_pair = mocker.patch(
        "funkwhale_api.federation.keys.get_key_pair",
        return_value=(b"private", b"public"),
    )

    tasks.rotate_actor_key(actor_id=actor.pk)

    actor.refresh_from_db()

    get_key_pair.assert_called_once_with()

    assert actor.public_key == "public"
    assert actor.private_key == "private"


def test_fetch_skipped(factories, r_mock):
    url = "https://fetch.object"
    fetch = factories["federation.Fetch"](url=url)
    payload = {"@context": jsonld.get_default_context(), "type": "Unhandled"}
    r_mock.get(url, json=payload)

    tasks.fetch(fetch_id=fetch.pk)

    fetch.refresh_from_db()

    assert fetch.status == "skipped"
    assert fetch.detail["reason"] == "unhandled_type"


@pytest.mark.parametrize(
    "r_mock_args, expected_error_code",
    [
        ({"json": {"type": "Unhandled"}}, "invalid_jsonld"),
        ({"json": {"@context": jsonld.get_default_context()}}, "invalid_jsonld"),
        ({"text": "invalidjson"}, "invalid_json"),
        ({"status_code": 404}, "http"),
        ({"status_code": 500}, "http"),
    ],
)
def test_fetch_errored(factories, r_mock_args, expected_error_code, r_mock):
    url = "https://fetch.object"
    fetch = factories["federation.Fetch"](url=url)
    r_mock.get(url, **r_mock_args)

    tasks.fetch(fetch_id=fetch.pk)

    fetch.refresh_from_db()

    assert fetch.status == "errored"
    assert fetch.detail["error_code"] == expected_error_code


def test_fetch_success(factories, r_mock, mocker):
    artist = factories["music.Artist"]()
    fetch = factories["federation.Fetch"](url=artist.fid)
    payload = serializers.ArtistSerializer(artist).data
    init = mocker.spy(serializers.ArtistSerializer, "__init__")
    save = mocker.spy(serializers.ArtistSerializer, "save")

    r_mock.get(artist.fid, json=payload)

    tasks.fetch(fetch_id=fetch.pk)

    fetch.refresh_from_db()

    assert fetch.status == "finished"
    assert init.call_count == 1
    assert init.call_args[0][1] == artist
    assert init.call_args[1]["data"] == payload
    assert save.call_count == 1


def test_fetch_webfinger(factories, r_mock, mocker):
    actor = factories["federation.Actor"]()
    fetch = factories["federation.Fetch"](
        url="webfinger://{}".format(actor.full_username)
    )
    payload = serializers.ActorSerializer(actor).data
    init = mocker.spy(serializers.ActorSerializer, "__init__")
    save = mocker.spy(serializers.ActorSerializer, "save")
    webfinger_payload = {
        "subject": "acct:{}".format(actor.full_username),
        "aliases": ["https://test.webfinger"],
        "links": [
            {"rel": "self", "type": "application/activity+json", "href": actor.fid}
        ],
    }
    webfinger_url = "https://{}/.well-known/webfinger?resource={}".format(
        actor.domain_id, webfinger_payload["subject"]
    )
    r_mock.get(actor.fid, json=payload)
    r_mock.get(webfinger_url, json=webfinger_payload)

    tasks.fetch(fetch_id=fetch.pk)

    fetch.refresh_from_db()

    assert fetch.status == "finished"
    assert fetch.object == actor
    assert init.call_count == 1
    assert init.call_args[0][1] == actor
    assert init.call_args[1]["data"] == payload
    assert save.call_count == 1


def test_fetch_rel_alternate(factories, r_mock, mocker):
    actor = factories["federation.Actor"]()
    fetch = factories["federation.Fetch"](url="http://example.page")
    html_text = """
    <html>
        <head>
            <link rel="alternate" type="application/activity+json" href="{}" />
        </head>
    </html>
    """.format(
        actor.fid
    )
    ap_payload = serializers.ActorSerializer(actor).data
    init = mocker.spy(serializers.ActorSerializer, "__init__")
    save = mocker.spy(serializers.ActorSerializer, "save")
    r_mock.get(fetch.url, text=html_text)
    r_mock.get(actor.fid, json=ap_payload)

    tasks.fetch(fetch_id=fetch.pk)

    fetch.refresh_from_db()

    assert fetch.status == "finished"
    assert fetch.object == actor
    assert init.call_count == 1
    assert init.call_args[0][1] == actor
    assert init.call_args[1]["data"] == ap_payload
    assert save.call_count == 1


@pytest.mark.parametrize(
    "factory_name, factory_kwargs, serializer_class",
    [
        ("federation.Actor", {}, serializers.ActorSerializer),
        ("music.Library", {}, serializers.LibrarySerializer),
        ("music.Artist", {}, serializers.ArtistSerializer),
        ("music.Album", {}, serializers.AlbumSerializer),
        ("music.Track", {}, serializers.TrackSerializer),
        (
            "music.Upload",
            {"bitrate": 200, "duration": 20},
            serializers.UploadSerializer,
        ),
        ("music.Upload", {"channel": True}, serializers.ChannelUploadSerializer),
    ],
)
def test_fetch_url(
    factory_name, factory_kwargs, serializer_class, factories, r_mock, mocker
):
    obj = factories[factory_name](**factory_kwargs)
    fetch = factories["federation.Fetch"](url=obj.fid)
    payload = serializer_class(obj).data
    init = mocker.spy(serializer_class, "__init__")
    save = mocker.spy(serializer_class, "save")

    r_mock.get(obj.fid, json=payload)

    tasks.fetch(fetch_id=fetch.pk)

    fetch.refresh_from_db()

    assert fetch.status == "finished"
    assert fetch.object == obj
    assert init.call_count == 1
    assert init.call_args[0][1] == obj
    assert init.call_args[1]["data"] == payload
    assert save.call_count == 1


def test_fetch_channel_actor_returns_channel_and_fetch_outbox(
    factories, r_mock, settings, mocker
):
    obj = factories["audio.Channel"]()
    fetch = factories["federation.Fetch"](url=obj.actor.fid)
    payload = serializers.ActorSerializer(obj.actor).data
    fetch_collection = mocker.patch.object(
        tasks, "fetch_collection", return_value={"next_page": "http://outbox.url/page2"}
    )
    fetch_collection_delayed = mocker.patch.object(tasks.fetch_collection, "delay")

    r_mock.get(obj.fid, json=payload)

    tasks.fetch(fetch_id=fetch.pk)

    fetch.refresh_from_db()

    assert fetch.status == "finished"
    assert fetch.object == obj
    fetch_collection.assert_called_once_with(
        obj.actor.outbox_url, channel_id=obj.pk, max_pages=1,
    )
    fetch_collection_delayed.assert_called_once_with(
        "http://outbox.url/page2",
        max_pages=settings.FEDERATION_COLLECTION_MAX_PAGES - 1,
        is_page=True,
        channel_id=obj.pk,
    )


def test_fetch_honor_instance_policy_domain(factories):
    domain = factories["moderation.InstancePolicy"](
        block_all=True, for_domain=True
    ).target_domain
    fid = "https://{}/test".format(domain.name)

    fetch = factories["federation.Fetch"](url=fid)
    tasks.fetch(fetch_id=fetch.pk)
    fetch.refresh_from_db()

    assert fetch.status == "errored"
    assert fetch.detail["error_code"] == "blocked"


def test_fetch_honor_mrf_inbox_before_http(mrf_inbox_registry, factories, mocker):
    apply = mocker.patch.object(mrf_inbox_registry, "apply", return_value=(None, False))
    fid = "http://domain/test"
    fetch = factories["federation.Fetch"](url=fid)
    tasks.fetch(fetch_id=fetch.pk)
    fetch.refresh_from_db()

    assert fetch.status == "errored"
    assert fetch.detail["error_code"] == "blocked"
    apply.assert_called_once_with({"id": fid})


def test_fetch_honor_mrf_inbox_after_http(
    r_mock, mrf_inbox_registry, factories, mocker
):
    apply = mocker.patch.object(
        mrf_inbox_registry, "apply", side_effect=[(True, False), (None, False)]
    )
    payload = {"id": "http://domain/test", "actor": "hello"}
    r_mock.get(payload["id"], json=payload)
    fetch = factories["federation.Fetch"](url=payload["id"])
    tasks.fetch(fetch_id=fetch.pk)
    fetch.refresh_from_db()

    assert fetch.status == "errored"
    assert fetch.detail["error_code"] == "blocked"

    apply.assert_any_call({"id": payload["id"]})
    apply.assert_any_call(payload)


def test_fetch_honor_instance_policy_different_url_and_id(r_mock, factories):
    domain = factories["moderation.InstancePolicy"](
        block_all=True, for_domain=True
    ).target_domain
    fid = "https://ok/test"
    r_mock.get(fid, json={"id": "http://{}/test".format(domain.name)})
    fetch = factories["federation.Fetch"](url=fid)
    tasks.fetch(fetch_id=fetch.pk)
    fetch.refresh_from_db()

    assert fetch.status == "errored"
    assert fetch.detail["error_code"] == "blocked"


def test_fetch_collection(mocker, r_mock):
    class DummySerializer(serializers.serializers.Serializer):
        def validate(self, validated_data):
            validated_data = self.initial_data
            if "id" not in validated_data["object"]:
                raise serializers.serializers.ValidationError()
            return validated_data

        def save(self):
            return self.initial_data

    mocker.patch.object(
        tasks,
        "COLLECTION_ACTIVITY_SERIALIZERS",
        [({"type": "Create", "object.type": "Audio"}, DummySerializer)],
    )
    payloads = {
        "outbox": {
            "id": "https://actor.url/outbox",
            "@context": jsonld.get_default_context(),
            "type": "OrderedCollection",
            "totalItems": 27094,
            "first": "https://actor.url/outbox?page=1",
            "last": "https://actor.url/outbox?page=3",
        },
        "page1": {
            "@context": jsonld.get_default_context(),
            "type": "OrderedCollectionPage",
            "next": "https://actor.url/outbox?page=2",
            "orderedItems": [
                {"type": "Unhandled"},
                {"type": "Unhandled"},
                {
                    "type": "Create",
                    "object": {"type": "Audio", "id": "https://actor.url/audio1"},
                },
            ],
        },
        "page2": {
            "@context": jsonld.get_default_context(),
            "type": "OrderedCollectionPage",
            "next": "https://actor.url/outbox?page=3",
            "orderedItems": [
                {"type": "Unhandled"},
                {
                    "type": "Create",
                    "object": {"type": "Audio", "id": "https://actor.url/audio2"},
                },
                {"type": "Unhandled"},
                {"type": "Create", "object": {"type": "Audio"}},
            ],
        },
    }
    r_mock.get(payloads["outbox"]["id"], json=payloads["outbox"])
    r_mock.get(payloads["outbox"]["first"], json=payloads["page1"])
    r_mock.get(payloads["page1"]["next"], json=payloads["page2"])
    result = tasks.fetch_collection(payloads["outbox"]["id"], max_pages=2,)
    assert result["items"] == [
        payloads["page1"]["orderedItems"][2],
        payloads["page2"]["orderedItems"][1],
    ]
    assert result["skipped"] == 4
    assert result["errored"] == 1
    assert result["seen"] == 7
    assert result["total"] == 27094
    assert result["next_page"] == payloads["page2"]["next"]

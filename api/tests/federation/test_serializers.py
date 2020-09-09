import io
import pytest
import uuid

from django.core.paginator import Paginator
from django.urls import reverse
from django.utils import timezone

from funkwhale_api.common import utils as common_utils
from funkwhale_api.federation import actors
from funkwhale_api.federation import contexts
from funkwhale_api.federation import keys
from funkwhale_api.federation import jsonld
from funkwhale_api.federation import models
from funkwhale_api.federation import serializers
from funkwhale_api.federation import utils
from funkwhale_api.moderation import serializers as moderation_serializers
from funkwhale_api.music import licenses


def test_actor_serializer_from_ap(db):
    private, public = keys.get_key_pair()
    actor_url = "https://test.federation/actor"
    payload = {
        "@context": jsonld.get_default_context(),
        "id": actor_url,
        "type": "Person",
        "outbox": "https://test.com/outbox",
        "inbox": "https://test.com/inbox",
        "following": "https://test.com/following",
        "followers": "https://test.com/followers",
        "preferredUsername": "test",
        "name": "Test",
        "summary": "Hello world",
        "manuallyApprovesFollowers": True,
        "url": "http://hello.world/path",
        "publicKey": {
            "publicKeyPem": public.decode("utf-8"),
            "owner": actor_url,
            "id": actor_url + "#main-key",
        },
        "endpoints": {"sharedInbox": "https://noop.url/federation/shared/inbox"},
        "icon": {
            "type": "Image",
            "mediaType": "image/jpeg",
            "url": "https://image.example/image.png",
        },
    }

    serializer = serializers.ActorSerializer(data=payload)
    assert serializer.is_valid(raise_exception=True)
    actor = serializer.save()

    assert actor.fid == actor_url
    assert actor.url == payload["url"]
    assert actor.inbox_url == payload["inbox"]
    assert actor.shared_inbox_url == payload["endpoints"]["sharedInbox"]
    assert actor.outbox_url == payload["outbox"]
    assert actor.following_url == payload["following"]
    assert actor.followers_url == payload["followers"]
    assert actor.followers_url == payload["followers"]
    assert actor.type == "Person"
    assert actor.preferred_username == payload["preferredUsername"]
    assert actor.name == payload["name"]
    assert actor.summary_obj.text == payload["summary"]
    assert actor.summary_obj.content_type == "text/html"
    assert actor.fid == actor_url
    assert actor.manually_approves_followers is True
    assert actor.private_key is None
    assert actor.public_key == payload["publicKey"]["publicKeyPem"]
    assert actor.domain_id == "test.federation"
    assert actor.attachment_icon.url == payload["icon"]["url"]
    assert actor.attachment_icon.mimetype == payload["icon"]["mediaType"]


def test_actor_serializer_from_ap_no_icon_mediaType(db):
    private, public = keys.get_key_pair()
    actor_url = "https://test.federation/actor"
    payload = {
        "@context": jsonld.get_default_context(),
        "id": actor_url,
        "type": "Person",
        "inbox": "https://test.com/inbox",
        "following": "https://test.com/following",
        "followers": "https://test.com/followers",
        "preferredUsername": "test",
        "manuallyApprovesFollowers": True,
        "url": "http://hello.world/path",
        "publicKey": {
            "publicKeyPem": public.decode("utf-8"),
            "owner": actor_url,
            "id": actor_url + "#main-key",
        },
        "endpoints": {"sharedInbox": "https://noop.url/federation/shared/inbox"},
        "icon": {"type": "Image", "url": "https://image.example/image.png"},
    }

    serializer = serializers.ActorSerializer(data=payload)
    assert serializer.is_valid(raise_exception=True)
    actor = serializer.save()

    assert actor.attachment_icon.url == payload["icon"]["url"]
    assert actor.attachment_icon.mimetype is None


def test_actor_serializer_only_mandatory_field_from_ap(db):
    payload = {
        "@context": jsonld.get_default_context(),
        "id": "https://test.federation/user",
        "type": "Person",
        "following": "https://test.federation/user/following",
        "followers": "https://test.federation/user/followers",
        "inbox": "https://test.federation/user/inbox",
        "outbox": "https://test.federation/user/outbox",
        "preferredUsername": "user",
    }

    serializer = serializers.ActorSerializer(data=payload)
    assert serializer.is_valid(raise_exception=True)

    actor = serializer.build()

    assert actor.fid == payload["id"]
    assert actor.inbox_url == payload["inbox"]
    assert actor.outbox_url == payload["outbox"]
    assert actor.followers_url == payload["followers"]
    assert actor.following_url == payload["following"]
    assert actor.preferred_username == payload["preferredUsername"]
    assert actor.domain.pk == "test.federation"
    assert actor.type == "Person"
    assert actor.manually_approves_followers is None


def test_actor_serializer_to_ap(factories):
    expected = {
        "@context": jsonld.get_default_context(),
        "id": "https://test.federation/user",
        "type": "Person",
        "following": "https://test.federation/user/following",
        "followers": "https://test.federation/user/followers",
        "inbox": "https://test.federation/user/inbox",
        "outbox": "https://test.federation/user/outbox",
        "preferredUsername": "user",
        "name": "Real User",
        "url": [{"type": "Link", "href": "https://test.url", "mediaType": "text/html"}],
        "manuallyApprovesFollowers": False,
        "publicKey": {
            "id": "https://test.federation/user#main-key",
            "owner": "https://test.federation/user",
            "publicKeyPem": "yolo",
        },
        "endpoints": {"sharedInbox": "https://test.federation/inbox"},
    }
    ac = models.Actor.objects.create(
        fid=expected["id"],
        inbox_url=expected["inbox"],
        outbox_url=expected["outbox"],
        url=expected["url"][0]["href"],
        shared_inbox_url=expected["endpoints"]["sharedInbox"],
        followers_url=expected["followers"],
        following_url=expected["following"],
        public_key=expected["publicKey"]["publicKeyPem"],
        preferred_username=expected["preferredUsername"],
        name=expected["name"],
        domain=models.Domain.objects.create(pk="test.domain"),
        type="Person",
        manually_approves_followers=False,
        attachment_icon=factories["common.Attachment"](),
    )

    content = common_utils.attach_content(
        ac, "summary_obj", {"text": "hello world", "content_type": "text/markdown"}
    )
    expected["summary"] = content.rendered
    expected["icon"] = {
        "type": "Image",
        "mediaType": "image/jpeg",
        "url": utils.full_url(ac.attachment_icon.file.url),
    }
    serializer = serializers.ActorSerializer(ac)

    assert serializer.data == expected


def test_webfinger_serializer():
    expected = {
        "subject": "acct:service@test.federation",
        "links": [
            {
                "rel": "self",
                "href": "https://test.federation/federation/instance/actor",
                "type": "application/activity+json",
            }
        ],
        "aliases": ["https://test.federation/federation/instance/actor"],
    }
    actor = models.Actor(
        fid=expected["links"][0]["href"],
        preferred_username="service",
        domain=models.Domain(pk="test.federation"),
    )
    serializer = serializers.ActorWebfingerSerializer(actor)

    assert serializer.data == expected


def test_follow_serializer_to_ap(factories):
    follow = factories["federation.Follow"](local=True)
    serializer = serializers.FollowSerializer(follow)

    expected = {
        "@context": jsonld.get_default_context(),
        "id": follow.get_federation_id(),
        "type": "Follow",
        "actor": follow.actor.fid,
        "object": follow.target.fid,
    }

    assert serializer.data == expected


def test_follow_serializer_save(factories):
    actor = factories["federation.Actor"]()
    target = factories["federation.Actor"]()

    data = {
        "id": "https://test.follow",
        "type": "Follow",
        "actor": actor.fid,
        "object": target.fid,
    }
    serializer = serializers.FollowSerializer(data=data)

    assert serializer.is_valid(raise_exception=True)

    follow = serializer.save()

    assert follow.pk is not None
    assert follow.actor == actor
    assert follow.target == target
    assert follow.approved is None


def test_follow_serializer_save_validates_on_context(factories):
    actor = factories["federation.Actor"]()
    target = factories["federation.Actor"]()
    impostor = factories["federation.Actor"]()

    data = {
        "id": "https://test.follow",
        "type": "Follow",
        "actor": actor.fid,
        "object": target.fid,
    }
    serializer = serializers.FollowSerializer(
        data=data, context={"follow_actor": impostor, "follow_target": impostor}
    )

    assert serializer.is_valid() is False

    assert "actor" in serializer.errors
    assert "object" in serializer.errors


def test_accept_follow_serializer_representation(factories):
    follow = factories["federation.Follow"](approved=None)

    expected = {
        "@context": jsonld.get_default_context(),
        "id": follow.get_federation_id() + "/accept",
        "type": "Accept",
        "actor": follow.target.fid,
        "object": serializers.FollowSerializer(follow).data,
    }

    serializer = serializers.AcceptFollowSerializer(follow)

    assert serializer.data == expected


def test_accept_follow_serializer_save(factories):
    follow = factories["federation.Follow"](approved=None)

    data = {
        "@context": jsonld.get_default_context(),
        "id": follow.get_federation_id() + "/accept",
        "type": "Accept",
        "actor": follow.target.fid,
        "object": serializers.FollowSerializer(follow).data,
    }

    serializer = serializers.AcceptFollowSerializer(data=data)
    assert serializer.is_valid(raise_exception=True)
    serializer.save()

    follow.refresh_from_db()

    assert follow.approved is True


def test_accept_follow_serializer_validates_on_context(factories):
    follow = factories["federation.Follow"](approved=None)
    impostor = factories["federation.Actor"]()
    data = {
        "@context": jsonld.get_default_context(),
        "id": follow.get_federation_id() + "/accept",
        "type": "Accept",
        "actor": impostor.url,
        "object": serializers.FollowSerializer(follow).data,
    }

    serializer = serializers.AcceptFollowSerializer(
        data=data, context={"follow_actor": impostor, "follow_target": impostor}
    )

    assert serializer.is_valid() is False
    assert "actor" in serializer.errors["object"]
    assert "object" in serializer.errors["object"]


def test_reject_follow_serializer_representation(factories):
    follow = factories["federation.Follow"](approved=None)

    expected = {
        "@context": jsonld.get_default_context(),
        "id": follow.get_federation_id() + "/reject",
        "type": "Reject",
        "actor": follow.target.fid,
        "object": serializers.FollowSerializer(follow).data,
    }

    serializer = serializers.RejectFollowSerializer(follow)

    assert serializer.data == expected


def test_undo_follow_serializer_representation(factories):
    follow = factories["federation.Follow"](approved=True)

    expected = {
        "@context": jsonld.get_default_context(),
        "id": follow.get_federation_id() + "/undo",
        "type": "Undo",
        "actor": follow.actor.fid,
        "object": serializers.FollowSerializer(follow).data,
    }

    serializer = serializers.UndoFollowSerializer(follow)

    assert serializer.data == expected


def test_undo_follow_serializer_save(factories):
    follow = factories["federation.Follow"](approved=True)

    data = {
        "@context": jsonld.get_default_context(),
        "id": follow.get_federation_id() + "/undo",
        "type": "Undo",
        "actor": follow.actor.fid,
        "object": serializers.FollowSerializer(follow).data,
    }

    serializer = serializers.UndoFollowSerializer(data=data)
    assert serializer.is_valid(raise_exception=True)
    serializer.save()

    with pytest.raises(models.Follow.DoesNotExist):
        follow.refresh_from_db()


def test_undo_follow_serializer_validates_on_context(factories):
    follow = factories["federation.Follow"](approved=True)
    impostor = factories["federation.Actor"]()
    data = {
        "@context": jsonld.get_default_context(),
        "id": follow.get_federation_id() + "/undo",
        "type": "Undo",
        "actor": impostor.url,
        "object": serializers.FollowSerializer(follow).data,
    }

    serializer = serializers.UndoFollowSerializer(
        data=data, context={"follow_actor": impostor, "follow_target": impostor}
    )

    assert serializer.is_valid() is False
    assert "actor" in serializer.errors["object"]
    assert "object" in serializer.errors["object"]


def test_paginated_collection_serializer(factories):
    uploads = factories["music.Upload"].create_batch(size=5)
    actor = factories["federation.Actor"](local=True)

    conf = {
        "id": "https://test.federation/test",
        "items": uploads,
        "item_serializer": serializers.UploadSerializer,
        "actor": actor,
        "page_size": 2,
    }
    expected = {
        "@context": jsonld.get_default_context(),
        "type": "Collection",
        "id": conf["id"],
        "attributedTo": actor.fid,
        "totalItems": len(uploads),
        "current": conf["id"] + "?page=1",
        "last": conf["id"] + "?page=3",
        "first": conf["id"] + "?page=1",
    }

    serializer = serializers.PaginatedCollectionSerializer(conf)

    assert serializer.data == expected


def test_paginated_collection_serializer_validation():
    data = {
        "@context": jsonld.get_default_context(),
        "type": "Collection",
        "id": "https://test.federation/test",
        "totalItems": 5,
        "actor": "http://test.actor",
        "attributedTo": "http://test.actor",
        "first": "https://test.federation/test?page=1",
        "last": "https://test.federation/test?page=1",
        "items": [],
    }

    serializer = serializers.PaginatedCollectionSerializer(data=data)

    assert serializer.is_valid(raise_exception=True) is True
    assert serializer.validated_data["totalItems"] == 5
    assert serializer.validated_data["id"] == data["id"]


def test_collection_page_serializer_validation():
    base = "https://test.federation/test"
    data = {
        "@context": jsonld.get_default_context(),
        "type": "CollectionPage",
        "id": base + "?page=2",
        "totalItems": 5,
        "actor": "https://test.actor",
        "attributedTo": "https://test.actor",
        "items": [],
        "first": "https://test.federation/test?page=1",
        "last": "https://test.federation/test?page=3",
        "prev": base + "?page=1",
        "next": base + "?page=3",
        "partOf": base,
    }

    serializer = serializers.CollectionPageSerializer(data=data)

    assert serializer.is_valid(raise_exception=True) is True
    assert serializer.validated_data["totalItems"] == 5
    assert serializer.validated_data["id"] == data["id"]
    assert serializer.validated_data["attributedTo"] == data["actor"]
    assert serializer.validated_data["items"] == []
    assert serializer.validated_data["prev"] == data["prev"]
    assert serializer.validated_data["next"] == data["next"]
    assert serializer.validated_data["partOf"] == data["partOf"]


def test_collection_page_serializer_can_validate_child():
    data = {
        "@context": jsonld.get_default_context(),
        "type": "CollectionPage",
        "id": "https://test.page?page=2",
        "attributedTo": "https://test.actor",
        "first": "https://test.page?page=1",
        "last": "https://test.page?page=3",
        "partOf": "https://test.page",
        "totalItems": 1,
        "items": [{"in": "valid"}],
    }

    serializer = serializers.CollectionPageSerializer(
        data=data, context={"item_serializer": serializers.UploadSerializer}
    )

    # child are validated but not included in data if not valid
    assert serializer.is_valid(raise_exception=True) is True
    assert len(serializer.validated_data["items"]) == 0


def test_collection_page_serializer(factories):
    uploads = factories["music.Upload"].create_batch(size=5)
    actor = factories["federation.Actor"](local=True)

    conf = {
        "id": "https://test.federation/test",
        "item_serializer": serializers.UploadSerializer,
        "actor": actor,
        "page": Paginator(uploads, 2).page(2),
    }
    expected = {
        "@context": jsonld.get_default_context(),
        "type": "CollectionPage",
        "id": conf["id"] + "?page=2",
        "attributedTo": actor.fid,
        "totalItems": len(uploads),
        "partOf": conf["id"],
        "prev": conf["id"] + "?page=1",
        "next": conf["id"] + "?page=3",
        "first": conf["id"] + "?page=1",
        "last": conf["id"] + "?page=3",
        "items": [
            conf["item_serializer"](
                i, context={"actor": actor, "include_ap_context": False}
            ).data
            for i in conf["page"].object_list
        ],
    }

    serializer = serializers.CollectionPageSerializer(conf)

    assert serializer.data == expected


def test_music_library_serializer_to_ap(factories):
    library = factories["music.Library"](privacy_level="everyone")
    # pending, errored and skippednot included
    factories["music.Upload"](import_status="pending")
    factories["music.Upload"](import_status="errored")
    factories["music.Upload"](import_status="finished")
    serializer = serializers.LibrarySerializer(library)
    expected = {
        "@context": jsonld.get_default_context(),
        "audience": "https://www.w3.org/ns/activitystreams#Public",
        "type": "Library",
        "id": library.fid,
        "name": library.name,
        "summary": library.description,
        "attributedTo": library.actor.fid,
        "totalItems": 0,
        "current": library.fid + "?page=1",
        "last": library.fid + "?page=1",
        "first": library.fid + "?page=1",
        "followers": library.followers_url,
    }

    assert serializer.data == expected


def test_music_library_serializer_from_public(factories, mocker):
    actor = factories["federation.Actor"]()
    retrieve = mocker.patch(
        "funkwhale_api.federation.utils.retrieve_ap_object", return_value=actor
    )
    data = {
        "@context": jsonld.get_default_context(),
        "audience": "https://www.w3.org/ns/activitystreams#Public",
        "name": "Hello",
        "summary": "World",
        "type": "Library",
        "id": "https://library.id",
        "followers": "https://library.id/followers",
        "attributedTo": actor.fid,
        "totalItems": 12,
        "first": "https://library.id?page=1",
        "last": "https://library.id?page=2",
    }
    serializer = serializers.LibrarySerializer(data=data)

    assert serializer.is_valid(raise_exception=True)

    library = serializer.save()

    assert library.actor == actor
    assert library.fid == data["id"]
    assert library.uploads_count == data["totalItems"]
    assert library.privacy_level == "everyone"
    assert library.name == "Hello"
    assert library.description == "World"
    assert library.followers_url == data["followers"]

    retrieve.assert_called_once_with(
        actor.fid,
        actor=None,
        queryset=actor.__class__,
        serializer_class=serializers.ActorSerializer,
    )


def test_music_library_serializer_from_private(factories, mocker):
    actor = factories["federation.Actor"]()
    retrieve = mocker.patch(
        "funkwhale_api.federation.utils.retrieve_ap_object", return_value=actor
    )
    data = {
        "@context": jsonld.get_default_context(),
        "audience": "",
        "name": "Hello",
        "summary": "World",
        "type": "Library",
        "id": "https://library.id",
        "followers": "https://library.id/followers",
        "attributedTo": actor.fid,
        "totalItems": 12,
        "first": "https://library.id?page=1",
        "last": "https://library.id?page=2",
    }
    serializer = serializers.LibrarySerializer(data=data)

    assert serializer.is_valid(raise_exception=True)

    library = serializer.save()

    assert library.actor == actor
    assert library.fid == data["id"]
    assert library.uploads_count == data["totalItems"]
    assert library.privacy_level == "me"
    assert library.name == "Hello"
    assert library.description == "World"
    assert library.followers_url == data["followers"]
    retrieve.assert_called_once_with(
        actor.fid,
        actor=None,
        queryset=actor.__class__,
        serializer_class=serializers.ActorSerializer,
    )


def test_music_library_serializer_from_ap_update(factories, mocker):
    actor = factories["federation.Actor"]()
    library = factories["music.Library"]()

    data = {
        "@context": jsonld.get_default_context(),
        "audience": "https://www.w3.org/ns/activitystreams#Public",
        "name": "Hello",
        "summary": "World",
        "type": "Library",
        "id": library.fid,
        "followers": "https://library.id/followers",
        "attributedTo": actor.fid,
        "totalItems": 12,
        "first": "https://library.id?page=1",
        "last": "https://library.id?page=2",
    }
    serializer = serializers.LibrarySerializer(library, data=data)

    assert serializer.is_valid(raise_exception=True)

    serializer.save()
    library.refresh_from_db()

    assert library.uploads_count == data["totalItems"]
    assert library.privacy_level == "everyone"
    assert library.name == "Hello"
    assert library.description == "World"
    assert library.followers_url == data["followers"]


def test_activity_pub_artist_serializer_to_ap(factories):
    content = factories["common.Content"]()
    artist = factories["music.Artist"](
        description=content, attributed=True, set_tags=["Punk", "Rock"], with_cover=True
    )
    expected = {
        "@context": jsonld.get_default_context(),
        "type": "Artist",
        "id": artist.fid,
        "name": artist.name,
        "musicbrainzId": artist.mbid,
        "published": artist.creation_date.isoformat(),
        "attributedTo": artist.attributed_to.fid,
        "mediaType": "text/html",
        "content": common_utils.render_html(content.text, content.content_type),
        "image": {
            "type": "Image",
            "mediaType": "image/jpeg",
            "url": utils.full_url(artist.attachment_cover.file.url),
        },
        "tag": [
            {"type": "Hashtag", "name": "#Punk"},
            {"type": "Hashtag", "name": "#Rock"},
        ],
    }
    serializer = serializers.ArtistSerializer(artist)

    assert serializer.data == expected


def test_activity_pub_artist_serializer_from_ap_create(factories, faker, now, mocker):
    actor = factories["federation.Actor"]()
    mocker.patch(
        "funkwhale_api.federation.utils.retrieve_ap_object", return_value=actor
    )
    payload = {
        "@context": jsonld.get_default_context(),
        "type": "Artist",
        "id": "https://test.artist",
        "name": "Art",
        "musicbrainzId": faker.uuid4(),
        "published": now.isoformat(),
        "attributedTo": actor.fid,
        "content": "Summary",
        "image": {
            "type": "Image",
            "mediaType": "image/jpeg",
            "url": "https://attachment.file",
        },
        "tag": [
            {"type": "Hashtag", "name": "#Punk"},
            {"type": "Hashtag", "name": "#Rock"},
        ],
    }
    serializer = serializers.ArtistSerializer(data=payload)
    assert serializer.is_valid(raise_exception=True) is True

    artist = serializer.save()

    assert artist.fid == payload["id"]
    assert artist.attributed_to == actor
    assert artist.name == payload["name"]
    assert str(artist.mbid) == payload["musicbrainzId"]
    assert artist.description.text == payload["content"]
    assert artist.description.content_type == "text/html"
    assert artist.attachment_cover.url == payload["image"]["url"]
    assert artist.attachment_cover.mimetype == payload["image"]["mediaType"]
    assert artist.get_tags() == ["Punk", "Rock"]


def test_activity_pub_artist_serializer_from_ap_update(factories, faker, now, mocker):
    artist = factories["music.Artist"]()
    actor = factories["federation.Actor"]()
    mocker.patch(
        "funkwhale_api.federation.utils.retrieve_ap_object", return_value=actor
    )
    payload = {
        "@context": jsonld.get_default_context(),
        "type": "Artist",
        "id": artist.fid,
        "name": "Art",
        "musicbrainzId": faker.uuid4(),
        "published": now.isoformat(),
        "attributedTo": actor.fid,
        "content": "Summary",
        "image": {
            "type": "Image",
            "mediaType": "image/jpeg",
            "url": "https://attachment.file",
        },
        "tag": [
            {"type": "Hashtag", "name": "#Punk"},
            {"type": "Hashtag", "name": "#Rock"},
        ],
    }
    serializer = serializers.ArtistSerializer(artist, data=payload)
    assert serializer.is_valid(raise_exception=True) is True
    serializer.save()
    artist.refresh_from_db()

    assert artist.attributed_to == actor
    assert artist.name == payload["name"]
    assert str(artist.mbid) == payload["musicbrainzId"]
    assert artist.description.text == payload["content"]
    assert artist.description.content_type == "text/html"
    assert artist.attachment_cover.url == payload["image"]["url"]
    assert artist.attachment_cover.mimetype == payload["image"]["mediaType"]
    assert artist.get_tags() == ["Punk", "Rock"]


def test_activity_pub_album_serializer_to_ap(factories):
    content = factories["common.Content"]()
    album = factories["music.Album"](
        description=content, attributed=True, set_tags=["Punk", "Rock"], with_cover=True
    )

    expected = {
        "@context": jsonld.get_default_context(),
        "type": "Album",
        "id": album.fid,
        "name": album.title,
        "image": {
            "type": "Image",
            "mediaType": "image/jpeg",
            "url": utils.full_url(album.attachment_cover.file.url),
        },
        "musicbrainzId": album.mbid,
        "published": album.creation_date.isoformat(),
        "released": album.release_date.isoformat(),
        "artists": [
            serializers.ArtistSerializer(
                album.artist, context={"include_ap_context": False}
            ).data
        ],
        "attributedTo": album.attributed_to.fid,
        "mediaType": "text/html",
        "content": common_utils.render_html(content.text, content.content_type),
        "tag": [
            {"type": "Hashtag", "name": "#Punk"},
            {"type": "Hashtag", "name": "#Rock"},
        ],
    }
    serializer = serializers.AlbumSerializer(album)

    assert serializer.data == expected


def test_activity_pub_album_serializer_to_ap_channel_artist(factories):
    channel = factories["audio.Channel"]()
    album = factories["music.Album"](artist=channel.artist,)

    serializer = serializers.AlbumSerializer(album)

    assert serializer.data["artists"] == [
        {"type": channel.actor.type, "id": channel.actor.fid}
    ]


def test_activity_pub_album_serializer_from_ap_create(factories, faker, now):
    actor = factories["federation.Actor"]()
    artist = factories["music.Artist"]()
    released = faker.date_object()
    payload = {
        "@context": jsonld.get_default_context(),
        "type": "Album",
        "id": "https://album.example",
        "name": faker.sentence(),
        "image": {"type": "Link", "mediaType": "image/jpeg", "href": faker.url()},
        "musicbrainzId": faker.uuid4(),
        "published": now.isoformat(),
        "released": released.isoformat(),
        "artists": [
            serializers.ArtistSerializer(
                artist, context={"include_ap_context": False}
            ).data
        ],
        "attributedTo": actor.fid,
        "tag": [
            {"type": "Hashtag", "name": "#Punk"},
            {"type": "Hashtag", "name": "#Rock"},
        ],
    }
    serializer = serializers.AlbumSerializer(data=payload)
    assert serializer.is_valid(raise_exception=True) is True

    album = serializer.save()

    assert album.title == payload["name"]
    assert str(album.mbid) == payload["musicbrainzId"]
    assert album.release_date == released
    assert album.artist == artist
    assert album.attachment_cover.url == payload["image"]["href"]
    assert album.attachment_cover.mimetype == payload["image"]["mediaType"]
    assert sorted(album.tagged_items.values_list("tag__name", flat=True)) == [
        "Punk",
        "Rock",
    ]


def test_activity_pub_album_serializer_from_ap_create_channel_artist(
    factories, faker, now
):
    actor = factories["federation.Actor"]()
    channel = factories["audio.Channel"]()
    released = faker.date_object()
    payload = {
        "@context": jsonld.get_default_context(),
        "type": "Album",
        "id": "https://album.example",
        "name": faker.sentence(),
        "published": now.isoformat(),
        "released": released.isoformat(),
        "artists": [{"type": channel.actor.type, "id": channel.actor.fid}],
        "attributedTo": actor.fid,
    }
    serializer = serializers.AlbumSerializer(data=payload)
    assert serializer.is_valid(raise_exception=True) is True

    album = serializer.save()

    assert album.artist == channel.artist


def test_activity_pub_album_serializer_from_ap_update(factories, faker):
    album = factories["music.Album"](attributed=True)
    released = faker.date_object()
    payload = {
        "@context": jsonld.get_default_context(),
        "type": "Album",
        "id": album.fid,
        "name": faker.sentence(),
        "image": {"type": "Link", "mediaType": "image/jpeg", "href": faker.url()},
        "musicbrainzId": faker.uuid4(),
        "published": album.creation_date.isoformat(),
        "released": released.isoformat(),
        "artists": [
            serializers.ArtistSerializer(
                album.artist, context={"include_ap_context": False}
            ).data
        ],
        "attributedTo": album.attributed_to.fid,
        "tag": [
            {"type": "Hashtag", "name": "#Punk"},
            {"type": "Hashtag", "name": "#Rock"},
        ],
    }
    serializer = serializers.AlbumSerializer(album, data=payload)
    assert serializer.is_valid(raise_exception=True) is True

    serializer.save()

    album.refresh_from_db()

    assert album.title == payload["name"]
    assert str(album.mbid) == payload["musicbrainzId"]
    assert album.release_date == released
    assert album.attachment_cover.url == payload["image"]["href"]
    assert album.attachment_cover.mimetype == payload["image"]["mediaType"]
    assert sorted(album.tagged_items.values_list("tag__name", flat=True)) == [
        "Punk",
        "Rock",
    ]


def test_activity_pub_track_serializer_to_ap(factories):
    content = factories["common.Content"]()
    track = factories["music.Track"](
        description=content,
        license="cc-by-4.0",
        copyright="test",
        disc_number=3,
        attributed=True,
        set_tags=["Punk", "Rock"],
        with_cover=True,
    )
    expected = {
        "@context": jsonld.get_default_context(),
        "published": track.creation_date.isoformat(),
        "type": "Track",
        "musicbrainzId": track.mbid,
        "id": track.fid,
        "name": track.title,
        "position": track.position,
        "disc": track.disc_number,
        "license": track.license.conf["identifiers"][0],
        "copyright": "test",
        "artists": [
            serializers.ArtistSerializer(
                track.artist, context={"include_ap_context": False}
            ).data
        ],
        "album": serializers.AlbumSerializer(
            track.album, context={"include_ap_context": False}
        ).data,
        "attributedTo": track.attributed_to.fid,
        "mediaType": "text/html",
        "content": common_utils.render_html(content.text, content.content_type),
        "tag": [
            {"type": "Hashtag", "name": "#Punk"},
            {"type": "Hashtag", "name": "#Rock"},
        ],
        "image": {
            "type": "Image",
            "mediaType": "image/jpeg",
            "url": utils.full_url(track.attachment_cover.file.url),
        },
    }
    serializer = serializers.TrackSerializer(track)

    assert serializer.data == expected


def test_activity_pub_track_serializer_from_ap(factories, r_mock, mocker):
    add_tags = mocker.patch("funkwhale_api.tags.models.add_tags")
    track_attributed_to = factories["federation.Actor"]()
    album_attributed_to = factories["federation.Actor"]()
    album_artist_attributed_to = factories["federation.Actor"]()
    artist_attributed_to = factories["federation.Actor"]()

    activity = factories["federation.Activity"]()
    published = timezone.now()
    released = timezone.now().date()
    data = {
        "@context": jsonld.get_default_context(),
        "type": "Track",
        "id": "http://hello.track",
        "published": published.isoformat(),
        "musicbrainzId": str(uuid.uuid4()),
        "name": "Black in back",
        "position": 5,
        "disc": 1,
        "content": "Hello there",
        "attributedTo": track_attributed_to.fid,
        "image": {
            "type": "Image",
            "url": "https://cover.image/track.png",
            "mediaType": "image/png",
        },
        "album": {
            "type": "Album",
            "id": "http://hello.album",
            "name": "Purple album",
            "musicbrainzId": str(uuid.uuid4()),
            "published": published.isoformat(),
            "released": released.isoformat(),
            "content": "Album summary",
            "mediaType": "text/markdown",
            "attributedTo": album_attributed_to.fid,
            "image": {
                "type": "Link",
                "href": "https://cover.image/test.png",
                "mediaType": "image/png",
            },
            "tag": [{"type": "Hashtag", "name": "AlbumTag"}],
            "artists": [
                {
                    "type": "Artist",
                    "mediaType": "text/plain",
                    "content": "Artist summary",
                    "id": "http://hello.artist",
                    "name": "John Smith",
                    "musicbrainzId": str(uuid.uuid4()),
                    "published": published.isoformat(),
                    "attributedTo": album_artist_attributed_to.fid,
                    "tag": [{"type": "Hashtag", "name": "AlbumArtistTag"}],
                    "image": {
                        "type": "Image",
                        "url": "https://cover.image/album-artist.png",
                        "mediaType": "image/png",
                    },
                }
            ],
        },
        "artists": [
            {
                "type": "Artist",
                "id": "http://hello.trackartist",
                "name": "Bob Smith",
                "mediaType": "text/plain",
                "content": "Other artist summary",
                "musicbrainzId": str(uuid.uuid4()),
                "attributedTo": artist_attributed_to.fid,
                "published": published.isoformat(),
                "tag": [{"type": "Hashtag", "name": "ArtistTag"}],
                "image": {
                    "type": "Image",
                    "url": "https://cover.image/artist.png",
                    "mediaType": "image/png",
                },
            }
        ],
        "tag": [
            {"type": "Hashtag", "name": "#Hello"},
            {"type": "Hashtag", "name": "World"},
        ],
    }
    serializer = serializers.TrackSerializer(data=data, context={"activity": activity})
    assert serializer.is_valid(raise_exception=True)

    track = serializer.save()
    album = track.album
    artist = track.artist
    album_artist = track.album.artist

    assert track.from_activity == activity
    assert track.fid == data["id"]
    assert track.title == data["name"]
    assert track.position == data["position"]
    assert track.disc_number == data["disc"]
    assert track.creation_date == published
    assert track.attributed_to == track_attributed_to
    assert str(track.mbid) == data["musicbrainzId"]
    assert track.description.text == data["content"]
    assert track.description.content_type == "text/html"
    assert track.attachment_cover.url == data["image"]["url"]
    assert track.attachment_cover.mimetype == data["image"]["mediaType"]

    assert album.from_activity == activity
    assert album.attachment_cover.url == data["album"]["image"]["href"]
    assert album.attachment_cover.mimetype == data["album"]["image"]["mediaType"]
    assert album.title == data["album"]["name"]
    assert album.fid == data["album"]["id"]
    assert str(album.mbid) == data["album"]["musicbrainzId"]
    assert album.creation_date == published
    assert album.release_date == released
    assert album.attributed_to == album_attributed_to
    assert album.description.text == data["album"]["content"]
    assert album.description.content_type == data["album"]["mediaType"]

    assert artist.from_activity == activity
    assert artist.name == data["artists"][0]["name"]
    assert artist.fid == data["artists"][0]["id"]
    assert str(artist.mbid) == data["artists"][0]["musicbrainzId"]
    assert artist.creation_date == published
    assert artist.attributed_to == artist_attributed_to
    assert artist.description.text == data["artists"][0]["content"]
    assert artist.description.content_type == data["artists"][0]["mediaType"]
    assert artist.attachment_cover.url == data["artists"][0]["image"]["url"]
    assert artist.attachment_cover.mimetype == data["artists"][0]["image"]["mediaType"]

    assert album_artist.from_activity == activity
    assert album_artist.name == data["album"]["artists"][0]["name"]
    assert album_artist.fid == data["album"]["artists"][0]["id"]
    assert str(album_artist.mbid) == data["album"]["artists"][0]["musicbrainzId"]
    assert album_artist.creation_date == published
    assert album_artist.attributed_to == album_artist_attributed_to
    assert album_artist.description.text == data["album"]["artists"][0]["content"]
    assert (
        album_artist.description.content_type
        == data["album"]["artists"][0]["mediaType"]
    )
    assert (
        album_artist.attachment_cover.url == data["album"]["artists"][0]["image"]["url"]
    )
    assert (
        album_artist.attachment_cover.mimetype
        == data["album"]["artists"][0]["image"]["mediaType"]
    )

    add_tags.assert_any_call(track, *["Hello", "World"])
    add_tags.assert_any_call(album, *["AlbumTag"])
    add_tags.assert_any_call(album_artist, *["AlbumArtistTag"])
    add_tags.assert_any_call(artist, *["ArtistTag"])


def test_activity_pub_track_serializer_from_ap_update(factories, r_mock, mocker, faker):
    set_tags = mocker.patch("funkwhale_api.tags.models.set_tags")
    content = factories["common.Content"]()
    track_attributed_to = factories["federation.Actor"]()
    track = factories["music.Track"](description=content)

    published = timezone.now()
    data = {
        "@context": jsonld.get_default_context(),
        "type": "Track",
        "id": track.fid,
        "published": published.isoformat(),
        "musicbrainzId": str(uuid.uuid4()),
        "name": "Black in back",
        "position": 5,
        "disc": 2,
        "content": "hello there",
        "attributedTo": track_attributed_to.fid,
        "album": serializers.AlbumSerializer(track.album).data,
        "artists": [serializers.ArtistSerializer(track.artist).data],
        "image": {"type": "Image", "mediaType": "image/jpeg", "url": faker.url()},
        "tag": [
            {"type": "Hashtag", "name": "#Hello"},
            # Ensure we can handle tags without a leading #
            {"type": "Hashtag", "name": "World"},
        ],
    }
    serializer = serializers.TrackSerializer(track, data=data)
    assert serializer.is_valid(raise_exception=True)

    serializer.save()
    track.refresh_from_db()

    assert track.fid == data["id"]
    assert track.title == data["name"]
    assert track.position == data["position"]
    assert track.disc_number == data["disc"]
    assert track.attributed_to == track_attributed_to
    assert track.description.content_type == "text/html"
    assert track.description.text == "hello there"
    assert str(track.mbid) == data["musicbrainzId"]
    assert track.attachment_cover.url == data["image"]["url"]
    assert track.attachment_cover.mimetype == data["image"]["mediaType"]

    set_tags.assert_called_once_with(track, *["Hello", "World"])

    with pytest.raises(content.DoesNotExist):
        content.refresh_from_db()


def test_activity_pub_upload_serializer_from_ap(factories, mocker, r_mock):
    activity = factories["federation.Activity"]()
    library = factories["music.Library"]()

    published = timezone.now()
    updated = timezone.now()
    released = timezone.now().date()
    data = {
        "@context": jsonld.get_default_context(),
        "type": "Audio",
        "id": "https://track.file",
        "name": "Ignored",
        "published": published.isoformat(),
        "updated": updated.isoformat(),
        "duration": 43,
        "bitrate": 42,
        "size": 66,
        "url": {"href": "https://audio.file", "type": "Link", "mediaType": "audio/mp3"},
        "library": library.fid,
        "track": {
            "type": "Track",
            "id": "http://hello.track",
            "published": published.isoformat(),
            "musicbrainzId": str(uuid.uuid4()),
            "name": "Black in back",
            "position": 5,
            "album": {
                "type": "Album",
                "id": "http://hello.album",
                "name": "Purple album",
                "musicbrainzId": str(uuid.uuid4()),
                "published": published.isoformat(),
                "released": released.isoformat(),
                "image": {
                    "type": "Link",
                    "href": "https://cover.image/test.png",
                    "mediaType": "image/png",
                },
                "artists": [
                    {
                        "type": "Artist",
                        "id": "http://hello.artist",
                        "name": "John Smith",
                        "musicbrainzId": str(uuid.uuid4()),
                        "published": published.isoformat(),
                    }
                ],
            },
            "artists": [
                {
                    "type": "Artist",
                    "id": "http://hello.trackartist",
                    "name": "Bob Smith",
                    "musicbrainzId": str(uuid.uuid4()),
                    "published": published.isoformat(),
                }
            ],
        },
    }
    r_mock.get(data["track"]["album"]["image"]["href"], body=io.BytesIO(b"coucou"))

    serializer = serializers.UploadSerializer(data=data, context={"activity": activity})
    assert serializer.is_valid(raise_exception=True)
    track_create = mocker.spy(serializers.TrackSerializer, "create")
    upload = serializer.save()

    assert upload.track.from_activity == activity
    assert upload.from_activity == activity
    assert track_create.call_count == 1
    assert upload.fid == data["id"]
    assert upload.track.fid == data["track"]["id"]
    assert upload.duration == data["duration"]
    assert upload.size == data["size"]
    assert upload.bitrate == data["bitrate"]
    assert upload.source == data["url"]["href"]
    assert upload.mimetype == data["url"]["mediaType"]
    assert upload.creation_date == published
    assert upload.import_status == "finished"
    assert upload.modification_date == updated


def test_activity_pub_upload_serializer_from_ap_update(factories, mocker, now, r_mock):
    library = factories["music.Library"]()
    upload = factories["music.Upload"](library=library, track__album__with_cover=True)

    data = {
        "@context": jsonld.get_default_context(),
        "type": "Audio",
        "id": upload.fid,
        "name": "Ignored",
        "published": now.isoformat(),
        "updated": now.isoformat(),
        "duration": 42,
        "bitrate": 42,
        "size": 66,
        "url": {
            "href": "https://audio.file/url",
            "type": "Link",
            "mediaType": "audio/mp3",
        },
        "library": library.fid,
        "track": serializers.TrackSerializer(upload.track).data,
    }
    r_mock.get(data["track"]["album"]["image"]["url"], body=io.BytesIO(b"coucou"))

    serializer = serializers.UploadSerializer(upload, data=data)
    assert serializer.is_valid(raise_exception=True)
    serializer.save()
    upload.refresh_from_db()

    assert upload.fid == data["id"]
    assert upload.duration == data["duration"]
    assert upload.size == data["size"]
    assert upload.bitrate == data["bitrate"]
    assert upload.source == data["url"]["href"]
    assert upload.mimetype == data["url"]["mediaType"]


def test_activity_pub_upload_serializer_validtes_library_actor(factories, mocker):
    library = factories["music.Library"]()
    usurpator = factories["federation.Actor"]()

    serializer = serializers.UploadSerializer(data={}, context={"actor": usurpator})

    with pytest.raises(serializers.serializers.ValidationError):
        serializer.validate_library(library.fid)


def test_activity_pub_audio_serializer_to_ap(factories):
    upload = factories["music.Upload"](
        mimetype="audio/mp3",
        bitrate=42,
        duration=43,
        size=44,
        library__privacy_level="everyone",
    )
    expected = {
        "@context": jsonld.get_default_context(),
        "type": "Audio",
        "id": upload.fid,
        "name": upload.track.full_name,
        "published": upload.creation_date.isoformat(),
        "updated": upload.modification_date.isoformat(),
        "duration": upload.duration,
        "bitrate": upload.bitrate,
        "size": upload.size,
        "to": contexts.AS.Public,
        "attributedTo": upload.library.actor.fid,
        "url": [
            {
                "href": utils.full_url(upload.listen_url_no_download),
                "type": "Link",
                "mediaType": "audio/mp3",
            },
            {
                "type": "Link",
                "mediaType": "text/html",
                "href": utils.full_url(upload.track.get_absolute_url()),
            },
        ],
        "library": upload.library.fid,
        "track": serializers.TrackSerializer(
            upload.track, context={"include_ap_context": False}
        ).data,
    }

    serializer = serializers.UploadSerializer(upload)

    assert serializer.data == expected


def test_local_actor_serializer_to_ap(factories, settings):
    expected = {
        "@context": jsonld.get_default_context(),
        "id": "https://test.federation/user",
        "type": "Person",
        "following": "https://test.federation/user/following",
        "followers": "https://test.federation/user/followers",
        "inbox": "https://test.federation/user/inbox",
        "outbox": "https://test.federation/user/outbox",
        "preferredUsername": "user",
        "name": "Real User",
        "summary": "Hello world",
        "manuallyApprovesFollowers": False,
        "publicKey": {
            "id": "https://test.federation/user#main-key",
            "owner": "https://test.federation/user",
            "publicKeyPem": "yolo",
        },
        "endpoints": {"sharedInbox": "https://test.federation/inbox"},
    }
    ac = models.Actor.objects.create(
        fid=expected["id"],
        inbox_url=expected["inbox"],
        outbox_url=expected["outbox"],
        shared_inbox_url=expected["endpoints"]["sharedInbox"],
        followers_url=expected["followers"],
        following_url=expected["following"],
        public_key=expected["publicKey"]["publicKeyPem"],
        preferred_username=expected["preferredUsername"],
        name=expected["name"],
        domain=models.Domain.objects.create(pk="test.federation"),
        type="Person",
        manually_approves_followers=False,
        attachment_icon=factories["common.Attachment"](),
    )
    content = common_utils.attach_content(
        ac, "summary_obj", {"text": "hello world", "content_type": "text/markdown"}
    )
    user = factories["users.User"]()
    user.actor = ac
    user.save()
    ac.refresh_from_db()
    expected["summary"] = content.rendered
    expected["url"] = [
        {
            "type": "Link",
            "href": "https://{}/@{}".format(
                settings.FUNKWHALE_HOSTNAME, ac.preferred_username
            ),
            "mediaType": "text/html",
        }
    ]
    expected["icon"] = {
        "type": "Image",
        "mediaType": "image/jpeg",
        "url": utils.full_url(ac.attachment_icon.file.url),
    }
    serializer = serializers.ActorSerializer(ac)

    assert serializer.data == expected


def test_activity_serializer_validate_recipients_empty(db):
    s = serializers.BaseActivitySerializer()

    with pytest.raises(serializers.serializers.ValidationError):
        s.validate_recipients({}, {})

    with pytest.raises(serializers.serializers.ValidationError):
        s.validate_recipients({"to": []}, {})

    with pytest.raises(serializers.serializers.ValidationError):
        s.validate_recipients({"cc": []}, {})


def test_activity_serializer_validate_recipients_context(db):
    s = serializers.BaseActivitySerializer(context={"recipients": ["dummy"]})

    assert s.validate_recipients({}, {}) is None


def test_track_serializer_update_license(factories):
    licenses.load(licenses.LICENSES)

    obj = factories["music.Track"](license=None)

    serializer = serializers.TrackSerializer(obj)
    serializer.update(obj, {"license": "http://creativecommons.org/licenses/by/2.0/"})

    obj.refresh_from_db()

    assert obj.license_id == "cc-by-2.0"


def test_channel_actor_serializer(factories):
    channel = factories["audio.Channel"](
        actor__attachment_icon=None,
        artist__with_cover=True,
        artist__set_tags=["punk", "rock"],
    )

    serializer = serializers.ActorSerializer(channel.actor)
    expected_url = [
        {
            "type": "Link",
            "href": channel.actor.get_absolute_url(),
            "mediaType": "text/html",
        },
        {
            "type": "Link",
            "href": channel.get_rss_url(),
            "mediaType": "application/rss+xml",
        },
    ]
    expected_icon = {
        "type": "Image",
        "mediaType": channel.artist.attachment_cover.mimetype,
        "url": channel.artist.attachment_cover.download_url_original,
    }
    assert serializer.data["url"] == expected_url
    assert serializer.data["icon"] == expected_icon
    assert serializer.data["attributedTo"] == channel.attributed_to.fid
    assert serializer.data["category"] == channel.artist.content_category
    assert serializer.data["tag"] == [
        {"type": "Hashtag", "name": "#punk"},
        {"type": "Hashtag", "name": "#rock"},
    ]


def test_channel_actor_serializer_from_ap_create(mocker, factories):
    domain = factories["federation.Domain"](name="test.pod")
    attributed_to = factories["federation.Actor"](domain=domain)
    get_actor = mocker.patch.object(actors, "get_actor", return_value=attributed_to)
    actor_data = {
        "@context": jsonld.get_default_context(),
        "followers": "https://test.pod/federation/actors/mychannel/followers",
        "preferredUsername": "mychannel",
        "id": "https://test.pod/federation/actors/mychannel",
        "endpoints": {"sharedInbox": "https://test.pod/federation/shared/inbox"},
        "name": "mychannel",
        "following": "https://test.pod/federation/actors/mychannel/following",
        "outbox": "https://test.pod/federation/actors/mychannel/outbox",
        "url": [
            {
                "mediaType": "text/html",
                "href": "https://test.pod/channels/mychannel",
                "type": "Link",
            },
            {
                "mediaType": "application/rss+xml",
                "href": "https://test.pod/api/v1/channels/mychannel/rss",
                "type": "Link",
            },
        ],
        "type": "Person",
        "category": "podcast",
        "attributedTo": attributed_to.fid,
        "manuallyApprovesFollowers": False,
        "inbox": "https://test.pod/federation/actors/mychannel/inbox",
        "icon": {
            "mediaType": "image/jpeg",
            "type": "Image",
            "url": "https://test.pod/media/attachments/dd/ce/b2/nosmile.jpeg",
        },
        "summary": "<p>content</p>",
        "publicKey": {
            "owner": "https://test.pod/federation/actors/mychannel",
            "publicKeyPem": "-----BEGIN RSA PUBLIC KEY-----\n+KwIDAQAB\n-----END RSA PUBLIC KEY-----\n",
            "id": "https://test.pod/federation/actors/mychannel#main-key",
        },
        "tag": [
            {"type": "Hashtag", "name": "#Indie"},
            {"type": "Hashtag", "name": "#Punk"},
            {"type": "Hashtag", "name": "#Rock"},
        ],
    }

    serializer = serializers.ActorSerializer(data=actor_data)
    assert serializer.is_valid(raise_exception=True) is True
    actor = serializer.save()

    get_actor.assert_called_once_with(actor_data["attributedTo"])
    assert actor.preferred_username == actor_data["preferredUsername"]
    assert actor.fid == actor_data["id"]
    assert actor.name == actor_data["name"]
    assert actor.type == actor_data["type"]
    assert actor.public_key == actor_data["publicKey"]["publicKeyPem"]
    assert actor.outbox_url == actor_data["outbox"]
    assert actor.inbox_url == actor_data["inbox"]
    assert actor.shared_inbox_url == actor_data["endpoints"]["sharedInbox"]
    assert actor.channel.attributed_to == attributed_to
    assert actor.channel.rss_url == actor_data["url"][1]["href"]
    assert actor.channel.artist.attributed_to == attributed_to
    assert actor.channel.artist.content_category == actor_data["category"]
    assert actor.channel.artist.name == actor_data["name"]
    assert actor.channel.artist.get_tags() == ["Indie", "Punk", "Rock"]
    assert actor.channel.artist.description.text == actor_data["summary"]
    assert actor.channel.artist.description.content_type == "text/html"
    assert actor.channel.artist.attachment_cover.url == actor_data["icon"]["url"]
    assert (
        actor.channel.artist.attachment_cover.mimetype
        == actor_data["icon"]["mediaType"]
    )
    assert actor.channel.library.fid is not None
    assert actor.channel.library.actor == attributed_to
    assert actor.channel.library.privacy_level == "everyone"
    assert actor.channel.library.name == actor_data["name"]


def test_channel_actor_serializer_from_ap_update(mocker, factories):
    domain = factories["federation.Domain"](name="test.pod")
    attributed_to = factories["federation.Actor"](domain=domain)
    actor = factories["federation.Actor"](domain=domain)
    channel = factories["audio.Channel"](actor=actor, attributed_to=attributed_to)
    get_actor = mocker.patch.object(actors, "get_actor", return_value=attributed_to)
    library = channel.library
    actor_data = {
        "@context": jsonld.get_default_context(),
        "followers": "https://test.pod/federation/actors/mychannel/followers",
        "preferredUsername": "mychannel",
        "id": actor.fid,
        "endpoints": {"sharedInbox": "https://test.pod/federation/shared/inbox"},
        "name": "mychannel",
        "following": "https://test.pod/federation/actors/mychannel/following",
        "outbox": "https://test.pod/federation/actors/mychannel/outbox",
        "url": [
            {
                "mediaType": "text/html",
                "href": "https://test.pod/channels/mychannel",
                "type": "Link",
            },
            {
                "mediaType": "application/rss+xml",
                "href": "https://test.pod/api/v1/channels/mychannel/rss",
                "type": "Link",
            },
        ],
        "type": "Person",
        "category": "podcast",
        "attributedTo": attributed_to.fid,
        "manuallyApprovesFollowers": False,
        "inbox": "https://test.pod/federation/actors/mychannel/inbox",
        "icon": {
            "mediaType": "image/jpeg",
            "type": "Image",
            "url": "https://test.pod/media/attachments/dd/ce/b2/nosmile.jpeg",
        },
        "summary": "<p>content</p>",
        "publicKey": {
            "owner": "https://test.pod/federation/actors/mychannel",
            "publicKeyPem": "-----BEGIN RSA PUBLIC KEY-----\n+KwIDAQAB\n-----END RSA PUBLIC KEY-----\n",
            "id": "https://test.pod/federation/actors/mychannel#main-key",
        },
        "tag": [
            {"type": "Hashtag", "name": "#Indie"},
            {"type": "Hashtag", "name": "#Punk"},
            {"type": "Hashtag", "name": "#Rock"},
        ],
    }

    serializer = serializers.ActorSerializer(data=actor_data)
    assert serializer.is_valid(raise_exception=True) is True
    serializer.save()
    channel.refresh_from_db()
    get_actor.assert_called_once_with(actor_data["attributedTo"])
    assert channel.actor == actor
    assert channel.attributed_to == attributed_to
    assert channel.rss_url == actor_data["url"][1]["href"]
    assert channel.artist.attributed_to == attributed_to
    assert channel.artist.content_category == actor_data["category"]
    assert channel.artist.name == actor_data["name"]
    assert channel.artist.get_tags() == ["Indie", "Punk", "Rock"]
    assert channel.artist.description.text == actor_data["summary"]
    assert channel.artist.description.content_type == "text/html"
    assert channel.artist.attachment_cover.url == actor_data["icon"]["url"]
    assert channel.artist.attachment_cover.mimetype == actor_data["icon"]["mediaType"]
    assert channel.library.actor == attributed_to
    assert channel.library.privacy_level == library.privacy_level
    assert channel.library.name == library.name


def test_channel_actor_outbox_serializer(factories):
    channel = factories["audio.Channel"]()
    uploads = factories["music.Upload"].create_batch(
        5,
        track__artist=channel.artist,
        library=channel.library,
        import_status="finished",
    )

    expected = {
        "@context": jsonld.get_default_context(),
        "type": "OrderedCollection",
        "id": channel.actor.outbox_url,
        "attributedTo": channel.actor.fid,
        "totalItems": len(uploads),
        "first": channel.actor.outbox_url + "?page=1",
        "last": channel.actor.outbox_url + "?page=1",
        "current": channel.actor.outbox_url + "?page=1",
    }

    serializer = serializers.ChannelOutboxSerializer(channel)

    assert serializer.data == expected


def test_channel_upload_serializer(factories):
    channel = factories["audio.Channel"](library__privacy_level="everyone")
    content = factories["common.Content"]()
    cover = factories["common.Attachment"]()
    upload = factories["music.Upload"](
        playable=True,
        bitrate=543,
        size=543,
        duration=54,
        library=channel.library,
        import_status="finished",
        track__set_tags=["Punk"],
        track__attachment_cover=cover,
        track__description=content,
        track__disc_number=3,
        track__position=12,
        track__license="cc0-1.0",
        track__copyright="Copyright something",
        track__album__set_tags=["Rock"],
        track__artist__set_tags=["Indie"],
    )

    expected = {
        "@context": jsonld.get_default_context(),
        "type": "Audio",
        "id": upload.fid,
        "name": upload.track.title,
        "summary": "#Indie #Punk #Rock",
        "attributedTo": channel.actor.fid,
        "published": upload.creation_date.isoformat(),
        "mediaType": "text/html",
        "content": common_utils.render_html(content.text, content.content_type),
        "to": "https://www.w3.org/ns/activitystreams#Public",
        "position": upload.track.position,
        "duration": upload.duration,
        "album": upload.track.album.fid,
        "disc": upload.track.disc_number,
        "copyright": upload.track.copyright,
        "license": upload.track.local_license["identifiers"][0],
        "url": [
            {
                "type": "Link",
                "mediaType": "text/html",
                "href": utils.full_url(upload.track.get_absolute_url()),
            },
            {
                "type": "Link",
                "mediaType": upload.mimetype,
                "href": utils.full_url(upload.listen_url_no_download),
                "bitrate": upload.bitrate,
                "size": upload.size,
            },
        ],
        "image": {
            "type": "Image",
            "url": upload.track.attachment_cover.download_url_original,
            "mediaType": upload.track.attachment_cover.mimetype,
        },
        "tag": [
            {"type": "Hashtag", "name": "#Indie"},
            {"type": "Hashtag", "name": "#Punk"},
            {"type": "Hashtag", "name": "#Rock"},
        ],
    }

    serializer = serializers.ChannelUploadSerializer(upload)

    assert serializer.data == expected


def test_channel_upload_serializer_from_ap_create(factories, now):
    channel = factories["audio.Channel"](library__privacy_level="everyone")
    album = factories["music.Album"](artist=channel.artist)
    payload = {
        "@context": jsonld.get_default_context(),
        "type": "Audio",
        "id": "https://test.pod/uuid",
        "name": "My test track",
        "summary": "#Indie #Punk #Rock",
        "attributedTo": channel.actor.fid,
        "published": now.isoformat(),
        "mediaType": "text/html",
        "content": "<p>Hello</p>",
        "duration": 543,
        "position": 4,
        "disc": 2,
        "album": album.fid,
        "to": "https://www.w3.org/ns/activitystreams#Public",
        "copyright": "Copyright test",
        "license": "http://creativecommons.org/publicdomain/zero/1.0/",
        "url": [
            {
                "type": "Link",
                "mediaType": "text/html",
                "href": "https://test.pod/track",
            },
            {
                "type": "Link",
                "mediaType": "audio/mpeg",
                "href": "https://test.pod/file.mp3",
                "bitrate": 192000,
                "size": 15492738,
            },
        ],
        "tag": [
            {"type": "Hashtag", "name": "#Indie"},
            {"type": "Hashtag", "name": "#Punk"},
            {"type": "Hashtag", "name": "#Rock"},
        ],
        "image": {
            "type": "Image",
            "mediaType": "image/jpeg",
            "url": "https://image.example/image.png",
        },
    }

    serializer = serializers.ChannelUploadSerializer(
        data=payload, context={"channel": channel}
    )
    assert serializer.is_valid(raise_exception=True) is True

    upload = serializer.save(channel=channel)

    assert upload.library == channel.library
    assert upload.import_status == "finished"
    assert upload.creation_date == now
    assert upload.fid == payload["id"]
    assert upload.source == payload["url"][1]["href"]
    assert upload.mimetype == payload["url"][1]["mediaType"]
    assert upload.size == payload["url"][1]["size"]
    assert upload.bitrate == payload["url"][1]["bitrate"]
    assert upload.duration == payload["duration"]
    assert upload.track.artist == channel.artist
    assert upload.track.position == payload["position"]
    assert upload.track.disc_number == payload["disc"]
    assert upload.track.attributed_to == channel.attributed_to
    assert upload.track.title == payload["name"]
    assert upload.track.creation_date == now
    assert upload.track.description.content_type == payload["mediaType"]
    assert upload.track.description.text == payload["content"]
    assert upload.track.fid == payload["id"]
    assert upload.track.license.pk == "cc0-1.0"
    assert upload.track.copyright == payload["copyright"]
    assert upload.track.get_tags() == ["Indie", "Punk", "Rock"]
    assert upload.track.attachment_cover.mimetype == payload["image"]["mediaType"]
    assert upload.track.attachment_cover.url == payload["image"]["url"]
    assert upload.track.album == album


def test_channel_upload_serializer_from_ap_update(factories, now):
    channel = factories["audio.Channel"](library__privacy_level="everyone")
    album = factories["music.Album"](artist=channel.artist)
    upload = factories["music.Upload"](track__album=album, track__artist=channel.artist)

    payload = {
        "@context": jsonld.get_default_context(),
        "type": "Audio",
        "id": upload.fid,
        "name": "Hello there",
        "attributedTo": channel.actor.fid,
        "published": now.isoformat(),
        "mediaType": "text/html",
        "content": "<p>Hello</p>",
        "duration": 543,
        "position": 4,
        "disc": 2,
        "album": album.fid,
        "to": "https://www.w3.org/ns/activitystreams#Public",
        "copyright": "Copyright test",
        "license": "http://creativecommons.org/publicdomain/zero/1.0/",
        "url": [
            {
                "type": "Link",
                "mediaType": "text/html",
                "href": "https://test.pod/track",
            },
            {
                "type": "Link",
                "mediaType": "audio/mpeg",
                "href": "https://test.pod/file.mp3",
                "bitrate": 192000,
                "size": 15492738,
            },
        ],
        "tag": [
            {"type": "Hashtag", "name": "#Indie"},
            {"type": "Hashtag", "name": "#Punk"},
            {"type": "Hashtag", "name": "#Rock"},
        ],
        "image": {
            "type": "Image",
            "mediaType": "image/jpeg",
            "url": "https://image.example/image.png",
        },
    }

    serializer = serializers.ChannelUploadSerializer(
        data=payload, context={"channel": channel}
    )
    assert serializer.is_valid(raise_exception=True) is True

    serializer.save(channel=channel)
    upload.refresh_from_db()

    assert upload.library == channel.library
    assert upload.import_status == "finished"
    assert upload.creation_date == now
    assert upload.fid == payload["id"]
    assert upload.source == payload["url"][1]["href"]
    assert upload.mimetype == payload["url"][1]["mediaType"]
    assert upload.size == payload["url"][1]["size"]
    assert upload.bitrate == payload["url"][1]["bitrate"]
    assert upload.duration == payload["duration"]
    assert upload.track.artist == channel.artist
    assert upload.track.position == payload["position"]
    assert upload.track.disc_number == payload["disc"]
    assert upload.track.attributed_to == channel.attributed_to
    assert upload.track.title == payload["name"]
    assert upload.track.creation_date == now
    assert upload.track.description.content_type == payload["mediaType"]
    assert upload.track.description.text == payload["content"]
    assert upload.track.fid == payload["id"]
    assert upload.track.license.pk == "cc0-1.0"
    assert upload.track.copyright == payload["copyright"]
    assert upload.track.get_tags() == ["Indie", "Punk", "Rock"]
    assert upload.track.attachment_cover.mimetype == payload["image"]["mediaType"]
    assert upload.track.attachment_cover.url == payload["image"]["url"]
    assert upload.track.album == album


def test_channel_create_upload_serializer(factories):
    channel = factories["audio.Channel"]()
    upload = factories["music.Upload"](
        playable=True, library=channel.library, import_status="finished"
    )

    expected = {
        "@context": jsonld.get_default_context(),
        "type": "Create",
        "id": utils.full_url(
            reverse("federation:music:uploads-activity", kwargs={"uuid": upload.uuid})
        ),
        "actor": upload.library.channel.actor.fid,
        "object": serializers.ChannelUploadSerializer(
            upload, context={"include_ap_context": False}
        ).data,
    }

    serializer = serializers.ChannelCreateUploadSerializer(upload)

    assert serializer.data == expected


def test_report_serializer_from_ap_create(factories, faker, now, mocker):
    actor = factories["federation.Actor"]()
    obj = factories["music.Artist"](local=True)
    payload = {
        "@context": jsonld.get_default_context(),
        "type": "Flag",
        "id": "https://test.report",
        "actor": actor.fid,
        "content": "hello world",
        "object": [obj.fid],
        "tag": [{"type": "Hashtag", "name": "#offensive_content"}],
    }
    serializer = serializers.FlagSerializer(data=payload, context={"actor": actor})
    assert serializer.is_valid(raise_exception=True) is True

    report = serializer.save()

    assert report.fid == payload["id"]
    assert report.summary == payload["content"]
    assert report.submitter == actor
    assert report.target == obj
    assert report.target_state == moderation_serializers.get_target_state(obj)
    assert report.target_owner == moderation_serializers.get_target_owner(obj)
    assert report.type == "offensive_content"


def test_report_serializer_to_ap(factories):
    report = factories["moderation.Report"](local=True)
    expected = {
        "@context": jsonld.get_default_context(),
        "type": "Flag",
        "id": report.fid,
        "actor": actors.get_service_actor().fid,
        "content": report.summary,
        "object": [report.target.fid],
        "tag": [{"type": "Hashtag", "name": "#{}".format(report.type)}],
    }
    serializer = serializers.FlagSerializer(report)
    assert serializer.data == expected

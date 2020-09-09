import pytest

from funkwhale_api.federation import (
    activity,
    actors,
    contexts,
    jsonld,
    routes,
    serializers,
)
from funkwhale_api.moderation import serializers as moderation_serializers


@pytest.mark.parametrize(
    "route,handler",
    [
        ({"type": "Follow"}, routes.inbox_follow),
        ({"type": "Accept"}, routes.inbox_accept),
        ({"type": "Reject"}, routes.inbox_reject_follow),
        ({"type": "Create", "object": {"type": "Audio"}}, routes.inbox_create_audio),
        (
            {"type": "Update", "object": {"type": "Library"}},
            routes.inbox_update_library,
        ),
        (
            {"type": "Delete", "object": {"type": "Library"}},
            routes.inbox_delete_library,
        ),
        ({"type": "Delete", "object": {"type": "Audio"}}, routes.inbox_delete_audio),
        ({"type": "Delete", "object": {"type": "Album"}}, routes.inbox_delete_album),
        ({"type": "Undo", "object": {"type": "Follow"}}, routes.inbox_undo_follow),
        ({"type": "Update", "object": {"type": "Artist"}}, routes.inbox_update_artist),
        ({"type": "Update", "object": {"type": "Album"}}, routes.inbox_update_album),
        ({"type": "Update", "object": {"type": "Track"}}, routes.inbox_update_track),
        ({"type": "Update", "object": {"type": "Audio"}}, routes.inbox_update_audio),
        ({"type": "Delete", "object": {"type": "Person"}}, routes.inbox_delete_actor),
        ({"type": "Delete", "object": {"type": "Tombstone"}}, routes.inbox_delete),
        ({"type": "Flag"}, routes.inbox_flag),
    ],
)
def test_inbox_routes(route, handler):
    matching = [
        handler for r, handler in routes.inbox.routes if activity.match_route(r, route)
    ]
    assert len(matching) == 1, "Inbox route {} not found".format(route)
    assert matching[0] == handler


@pytest.mark.parametrize(
    "route,handler",
    [
        ({"type": "Accept"}, routes.outbox_accept),
        ({"type": "Flag"}, routes.outbox_flag),
        ({"type": "Follow"}, routes.outbox_follow),
        ({"type": "Reject"}, routes.outbox_reject_follow),
        ({"type": "Create", "object": {"type": "Audio"}}, routes.outbox_create_audio),
        (
            {"type": "Update", "object": {"type": "Library"}},
            routes.outbox_update_library,
        ),
        (
            {"type": "Delete", "object": {"type": "Library"}},
            routes.outbox_delete_library,
        ),
        ({"type": "Delete", "object": {"type": "Audio"}}, routes.outbox_delete_audio),
        ({"type": "Delete", "object": {"type": "Album"}}, routes.outbox_delete_album),
        ({"type": "Undo", "object": {"type": "Follow"}}, routes.outbox_undo_follow),
        ({"type": "Update", "object": {"type": "Track"}}, routes.outbox_update_track),
        ({"type": "Update", "object": {"type": "Audio"}}, routes.outbox_update_audio),
        (
            {"type": "Delete", "object": {"type": "Tombstone"}},
            routes.outbox_delete_actor,
        ),
        ({"type": "Delete", "object": {"type": "Person"}}, routes.outbox_delete_actor),
        ({"type": "Delete", "object": {"type": "Service"}}, routes.outbox_delete_actor),
        (
            {"type": "Delete", "object": {"type": "Application"}},
            routes.outbox_delete_actor,
        ),
        ({"type": "Delete", "object": {"type": "Group"}}, routes.outbox_delete_actor),
        (
            {"type": "Delete", "object": {"type": "Organization"}},
            routes.outbox_delete_actor,
        ),
    ],
)
def test_outbox_routes(route, handler):
    matching = [
        handler for r, handler in routes.outbox.routes if activity.match_route(r, route)
    ]
    assert len(matching) == 1, "Outbox route {} not found".format(route)
    assert matching[0] == handler


def test_inbox_follow_library_autoapprove(factories, mocker):
    mocked_outbox_dispatch = mocker.patch(
        "funkwhale_api.federation.activity.OutboxRouter.dispatch"
    )

    local_actor = factories["users.User"]().create_actor()
    remote_actor = factories["federation.Actor"]()
    library = factories["music.Library"](actor=local_actor, privacy_level="everyone")
    ii = factories["federation.InboxItem"](actor=local_actor)

    payload = {
        "type": "Follow",
        "id": "https://test.follow",
        "actor": remote_actor.fid,
        "object": library.fid,
    }

    result = routes.inbox_follow(
        payload,
        context={"actor": remote_actor, "inbox_items": [ii], "raise_exception": True},
    )
    follow = library.received_follows.latest("id")

    assert result["object"] == library
    assert result["related_object"] == follow

    assert follow.fid == payload["id"]
    assert follow.actor == remote_actor
    assert follow.approved is True

    mocked_outbox_dispatch.assert_called_once_with(
        {"type": "Accept"}, context={"follow": follow}
    )


def test_inbox_follow_channel_autoapprove(factories, mocker):
    mocked_outbox_dispatch = mocker.patch(
        "funkwhale_api.federation.activity.OutboxRouter.dispatch"
    )

    local_actor = factories["users.User"]().create_actor()
    remote_actor = factories["federation.Actor"]()
    channel = factories["audio.Channel"](attributed_to=local_actor)
    ii = factories["federation.InboxItem"](actor=channel.actor)

    payload = {
        "type": "Follow",
        "id": "https://test.follow",
        "actor": remote_actor.fid,
        "object": channel.actor.fid,
    }

    result = routes.inbox_follow(
        payload,
        context={"actor": remote_actor, "inbox_items": [ii], "raise_exception": True},
    )
    follow = channel.actor.received_follows.latest("id")

    assert result["object"] == channel.actor
    assert result["related_object"] == follow

    assert follow.fid == payload["id"]
    assert follow.actor == remote_actor
    assert follow.approved is True

    mocked_outbox_dispatch.assert_called_once_with(
        {"type": "Accept"}, context={"follow": follow}
    )


def test_inbox_follow_library_manual_approve(factories, mocker):
    mocked_outbox_dispatch = mocker.patch(
        "funkwhale_api.federation.activity.OutboxRouter.dispatch"
    )

    local_actor = factories["users.User"]().create_actor()
    remote_actor = factories["federation.Actor"]()
    library = factories["music.Library"](actor=local_actor, privacy_level="me")
    ii = factories["federation.InboxItem"](actor=local_actor)

    payload = {
        "type": "Follow",
        "id": "https://test.follow",
        "actor": remote_actor.fid,
        "object": library.fid,
    }

    result = routes.inbox_follow(
        payload,
        context={"actor": remote_actor, "inbox_items": [ii], "raise_exception": True},
    )
    follow = library.received_follows.latest("id")

    assert result["object"] == library
    assert result["related_object"] == follow

    assert follow.fid == payload["id"]
    assert follow.actor == remote_actor
    assert follow.approved is None

    mocked_outbox_dispatch.assert_not_called()


def test_inbox_follow_library_already_approved(factories, mocker):
    """Cf #830, out of sync follows"""
    mocked_outbox_dispatch = mocker.patch(
        "funkwhale_api.federation.activity.OutboxRouter.dispatch"
    )

    local_actor = factories["users.User"]().create_actor()
    remote_actor = factories["federation.Actor"]()
    library = factories["music.Library"](actor=local_actor, privacy_level="me")
    ii = factories["federation.InboxItem"](actor=local_actor)
    existing_follow = factories["federation.LibraryFollow"](
        target=library, actor=remote_actor, approved=True
    )
    payload = {
        "type": "Follow",
        "id": "https://test.follow",
        "actor": remote_actor.fid,
        "object": library.fid,
    }

    result = routes.inbox_follow(
        payload,
        context={"actor": remote_actor, "inbox_items": [ii], "raise_exception": True},
    )
    follow = library.received_follows.latest("id")

    assert result["object"] == library
    assert result["related_object"] == follow

    assert follow.fid == payload["id"]
    assert follow.actor == remote_actor
    assert follow.approved is True
    assert follow.uuid != existing_follow.uuid
    mocked_outbox_dispatch.assert_called_once_with(
        {"type": "Accept"}, context={"follow": follow}
    )


def test_outbox_accept(factories, mocker):
    remote_actor = factories["federation.Actor"]()
    follow = factories["federation.LibraryFollow"](actor=remote_actor)

    activity = list(routes.outbox_accept({"follow": follow}))[0]

    serializer = serializers.AcceptFollowSerializer(
        follow, context={"actor": follow.target.actor}
    )
    expected = serializer.data
    expected["to"] = [follow.actor]

    assert activity["payload"] == expected
    assert activity["actor"] == follow.target.actor
    assert activity["object"] == follow


def test_inbox_accept(factories, mocker):
    mocked_scan = mocker.patch("funkwhale_api.music.models.Library.schedule_scan")
    local_actor = factories["users.User"]().create_actor()
    remote_actor = factories["federation.Actor"]()
    follow = factories["federation.LibraryFollow"](
        actor=local_actor, target__actor=remote_actor
    )
    assert follow.approved is None
    serializer = serializers.AcceptFollowSerializer(
        follow, context={"actor": remote_actor}
    )
    ii = factories["federation.InboxItem"](actor=local_actor)
    result = routes.inbox_accept(
        serializer.data,
        context={"actor": remote_actor, "inbox_items": [ii], "raise_exception": True},
    )
    assert result["object"] == follow
    assert result["related_object"] == follow.target

    follow.refresh_from_db()

    assert follow.approved is True
    mocked_scan.assert_called_once_with(actor=follow.actor)


def test_outbox_follow_library(factories, mocker):
    follow = factories["federation.LibraryFollow"]()
    activity = list(routes.outbox_follow({"follow": follow}))[0]
    serializer = serializers.FollowSerializer(follow, context={"actor": follow.actor})
    expected = serializer.data
    expected["to"] = [follow.target.actor]

    assert activity["payload"] == expected
    assert activity["actor"] == follow.actor
    assert activity["object"] == follow.target


def test_outbox_create_audio(factories, mocker):
    upload = factories["music.Upload"]()
    activity = list(routes.outbox_create_audio({"upload": upload}))[0]
    serializer = serializers.ActivitySerializer(
        {
            "type": "Create",
            "object": serializers.UploadSerializer(upload).data,
            "actor": upload.library.actor.fid,
        }
    )
    expected = serializer.data
    expected["to"] = [{"type": "followers", "target": upload.library}]

    assert dict(activity["payload"]) == dict(expected)
    assert activity["actor"] == upload.library.actor
    assert activity["target"] == upload.library
    assert activity["object"] == upload


def test_outbox_create_audio_channel(factories, mocker):
    channel = factories["audio.Channel"]()
    upload = factories["music.Upload"](library=channel.library)
    activity = list(routes.outbox_create_audio({"upload": upload}))[0]
    serializer = serializers.ChannelCreateUploadSerializer(upload)
    expected = serializer.data
    expected["to"] = [{"type": "followers", "target": upload.library.channel.actor}]

    assert dict(activity["payload"]) == dict(expected)
    assert activity["actor"] == channel.actor
    assert activity["target"] is None
    assert activity["object"] == upload


def test_inbox_create_audio(factories, mocker):
    activity = factories["federation.Activity"]()
    upload = factories["music.Upload"](
        bitrate=42, duration=55, track__album__with_cover=True
    )
    payload = {
        "@context": jsonld.get_default_context(),
        "type": "Create",
        "actor": upload.library.actor.fid,
        "object": serializers.UploadSerializer(upload).data,
    }
    library = upload.library
    upload.delete()
    init = mocker.spy(serializers.UploadSerializer, "__init__")
    save = mocker.spy(serializers.UploadSerializer, "save")
    assert library.uploads.count() == 0
    result = routes.inbox_create_audio(
        payload,
        context={"actor": library.actor, "raise_exception": True, "activity": activity},
    )
    assert library.uploads.count() == 1
    assert result == {"object": library.uploads.latest("id"), "target": library}

    assert init.call_count == 1
    args = init.call_args
    assert args[1]["data"] == payload["object"]
    assert args[1]["context"] == {"activity": activity, "actor": library.actor}
    assert save.call_count == 1


def test_inbox_create_audio_channel(factories, mocker):
    activity = factories["federation.Activity"]()
    channel = factories["audio.Channel"]()
    album = factories["music.Album"](artist=channel.artist)
    upload = factories["music.Upload"](track__album=album, library=channel.library,)
    payload = {
        "@context": jsonld.get_default_context(),
        "type": "Create",
        "actor": channel.actor.fid,
        "object": serializers.ChannelUploadSerializer(upload).data,
    }
    upload.delete()
    init = mocker.spy(serializers.ChannelCreateUploadSerializer, "__init__")
    save = mocker.spy(serializers.ChannelCreateUploadSerializer, "save")
    result = routes.inbox_create_audio(
        payload,
        context={"actor": channel.actor, "raise_exception": True, "activity": activity},
    )
    assert channel.library.uploads.count() == 1
    assert result == {"object": channel.library.uploads.latest("id"), "target": channel}

    assert init.call_count == 1
    args = init.call_args
    assert args[1]["data"] == payload
    assert args[1]["context"] == {"channel": channel}
    assert save.call_count == 1


def test_inbox_delete_library(factories):
    activity = factories["federation.Activity"]()

    library = factories["music.Library"]()
    payload = {
        "type": "Delete",
        "actor": library.actor.fid,
        "object": {"type": "Library", "id": library.fid},
    }

    routes.inbox_delete_library(
        payload,
        context={"actor": library.actor, "raise_exception": True, "activity": activity},
    )

    with pytest.raises(library.__class__.DoesNotExist):
        library.refresh_from_db()


def test_inbox_delete_album(factories):

    album = factories["music.Album"](attributed=True)
    payload = {
        "type": "Delete",
        "actor": album.attributed_to.fid,
        "object": {"type": "Album", "id": album.fid},
    }

    routes.inbox_delete_album(
        payload,
        context={
            "actor": album.attributed_to,
            "raise_exception": True,
            "activity": activity,
        },
    )

    with pytest.raises(album.__class__.DoesNotExist):
        album.refresh_from_db()


def test_inbox_delete_album_channel(factories):
    channel = factories["audio.Channel"]()
    album = factories["music.Album"](artist=channel.artist)
    payload = {
        "type": "Delete",
        "actor": channel.actor.fid,
        "object": {"type": "Album", "id": album.fid},
    }

    routes.inbox_delete_album(
        payload,
        context={"actor": channel.actor, "raise_exception": True, "activity": activity},
    )

    with pytest.raises(album.__class__.DoesNotExist):
        album.refresh_from_db()


def test_outbox_delete_album(factories):
    album = factories["music.Album"](attributed=True)
    a = list(routes.outbox_delete_album({"album": album}))[0]
    expected = serializers.ActivitySerializer(
        {"type": "Delete", "object": {"type": "Album", "id": album.fid}}
    ).data

    expected["to"] = [activity.PUBLIC_ADDRESS, {"type": "instances_with_followers"}]

    assert dict(a["payload"]) == dict(expected)
    assert a["actor"] == album.attributed_to


def test_outbox_delete_album_channel(factories):
    channel = factories["audio.Channel"]()
    album = factories["music.Album"](artist=channel.artist)
    a = list(routes.outbox_delete_album({"album": album}))[0]
    expected = serializers.ActivitySerializer(
        {"type": "Delete", "object": {"type": "Album", "id": album.fid}}
    ).data

    expected["to"] = [activity.PUBLIC_ADDRESS, {"type": "instances_with_followers"}]

    assert dict(a["payload"]) == dict(expected)
    assert a["actor"] == channel.actor


def test_inbox_delete_library_impostor(factories):
    activity = factories["federation.Activity"]()
    impostor = factories["federation.Actor"]()
    library = factories["music.Library"]()
    payload = {
        "type": "Delete",
        "actor": library.actor.fid,
        "object": {"type": "Library", "id": library.fid},
    }

    routes.inbox_delete_library(
        payload,
        context={"actor": impostor, "raise_exception": True, "activity": activity},
    )

    # not deleted, should still be here
    library.refresh_from_db()


def test_outbox_delete_library(factories):
    library = factories["music.Library"]()
    activity = list(routes.outbox_delete_library({"library": library}))[0]
    expected = serializers.ActivitySerializer(
        {"type": "Delete", "object": {"type": "Library", "id": library.fid}}
    ).data

    expected["to"] = [{"type": "followers", "target": library}]

    assert dict(activity["payload"]) == dict(expected)
    assert activity["actor"] == library.actor


def test_outbox_update_library(factories):
    library = factories["music.Library"]()
    activity = list(routes.outbox_update_library({"library": library}))[0]
    expected = serializers.ActivitySerializer(
        {"type": "Update", "object": serializers.LibrarySerializer(library).data}
    ).data

    expected["to"] = [{"type": "followers", "target": library}]

    assert dict(activity["payload"]) == dict(expected)
    assert activity["actor"] == library.actor


def test_inbox_update_library(factories):
    activity = factories["federation.Activity"]()

    library = factories["music.Library"]()
    data = serializers.LibrarySerializer(library).data
    data["name"] = "New name"
    payload = {"type": "Update", "actor": library.actor.fid, "object": data}

    routes.inbox_update_library(
        payload,
        context={"actor": library.actor, "raise_exception": True, "activity": activity},
    )

    library.refresh_from_db()
    assert library.name == "New name"


# def test_inbox_update_library_impostor(factories):
#     activity = factories["federation.Activity"]()
#     impostor = factories["federation.Actor"]()
#     library = factories["music.Library"]()
#     payload = {
#         "type": "Delete",
#         "actor": library.actor.fid,
#         "object": {"type": "Library", "id": library.fid},
#     }

#     routes.inbox_update_library(
#         payload,
#         context={"actor": impostor, "raise_exception": True, "activity": activity},
#     )

#     # not deleted, should still be here
#     library.refresh_from_db()


def test_inbox_delete_audio(factories):
    activity = factories["federation.Activity"]()

    upload = factories["music.Upload"]()
    library = upload.library
    payload = {
        "type": "Delete",
        "actor": library.actor.fid,
        "object": {"type": "Audio", "id": [upload.fid]},
    }

    routes.inbox_delete_audio(
        payload,
        context={"actor": library.actor, "raise_exception": True, "activity": activity},
    )

    with pytest.raises(upload.__class__.DoesNotExist):
        upload.refresh_from_db()


def test_inbox_delete_audio_channel(factories):
    activity = factories["federation.Activity"]()
    channel = factories["audio.Channel"]()
    upload = factories["music.Upload"](track__artist=channel.artist)
    payload = {
        "type": "Delete",
        "actor": channel.actor.fid,
        "object": {"type": "Audio", "id": [upload.fid]},
    }

    routes.inbox_delete_audio(
        payload,
        context={"actor": channel.actor, "raise_exception": True, "activity": activity},
    )

    with pytest.raises(upload.__class__.DoesNotExist):
        upload.refresh_from_db()


def test_inbox_delete_audio_impostor(factories):
    activity = factories["federation.Activity"]()
    impostor = factories["federation.Actor"]()
    upload = factories["music.Upload"]()
    library = upload.library
    payload = {
        "type": "Delete",
        "actor": library.actor.fid,
        "object": {"type": "Audio", "id": [upload.fid]},
    }

    routes.inbox_delete_audio(
        payload,
        context={"actor": impostor, "raise_exception": True, "activity": activity},
    )

    # not deleted, should still be here
    upload.refresh_from_db()


def test_outbox_delete_audio(factories):
    upload = factories["music.Upload"]()
    activity = list(routes.outbox_delete_audio({"uploads": [upload]}))[0]
    expected = serializers.ActivitySerializer(
        {"type": "Delete", "object": {"type": "Audio", "id": [upload.fid]}}
    ).data

    expected["to"] = [{"type": "followers", "target": upload.library}]

    assert dict(activity["payload"]) == dict(expected)
    assert activity["actor"] == upload.library.actor


def test_outbox_delete_audio_channel(factories):
    channel = factories["audio.Channel"]()
    upload = factories["music.Upload"](library=channel.library)
    activity = list(routes.outbox_delete_audio({"uploads": [upload]}))[0]
    expected = serializers.ActivitySerializer(
        {"type": "Delete", "object": {"type": "Audio", "id": [upload.fid]}}
    ).data

    expected["to"] = [{"type": "followers", "target": channel.actor}]

    assert dict(activity["payload"]) == dict(expected)
    assert activity["actor"] == channel.actor


def test_inbox_delete_follow_library(factories):
    local_actor = factories["users.User"]().create_actor()
    remote_actor = factories["federation.Actor"]()
    follow = factories["federation.LibraryFollow"](
        actor=local_actor, target__actor=remote_actor, approved=True
    )
    assert follow.approved is True
    serializer = serializers.UndoFollowSerializer(
        follow, context={"actor": local_actor}
    )
    ii = factories["federation.InboxItem"](actor=local_actor)
    routes.inbox_undo_follow(
        serializer.data,
        context={"actor": local_actor, "inbox_items": [ii], "raise_exception": True},
    )
    with pytest.raises(follow.__class__.DoesNotExist):
        follow.refresh_from_db()


def test_outbox_delete_follow_library(factories):
    remote_actor = factories["federation.Actor"]()
    local_actor = factories["federation.Actor"](local=True)
    follow = factories["federation.LibraryFollow"](
        actor=local_actor, target__actor=remote_actor
    )

    activity = list(routes.outbox_undo_follow({"follow": follow}))[0]

    serializer = serializers.UndoFollowSerializer(
        follow, context={"actor": follow.actor}
    )
    expected = serializer.data
    expected["to"] = [follow.target.actor]

    assert activity["payload"] == expected
    assert activity["actor"] == follow.actor
    assert activity["object"] == follow
    assert activity["related_object"] == follow.target


def test_inbox_reject_follow_library(factories):
    local_actor = factories["users.User"]().create_actor()
    remote_actor = factories["federation.Actor"]()
    follow = factories["federation.LibraryFollow"](
        actor=local_actor, target__actor=remote_actor, approved=True
    )
    assert follow.approved is True
    serializer = serializers.RejectFollowSerializer(
        follow, context={"actor": remote_actor}
    )
    ii = factories["federation.InboxItem"](actor=local_actor)
    routes.inbox_reject_follow(
        serializer.data,
        context={"actor": remote_actor, "inbox_items": [ii], "raise_exception": True},
    )
    follow.refresh_from_db()
    assert follow.approved is False


def test_outbox_reject_follow_library(factories):
    remote_actor = factories["federation.Actor"]()
    local_actor = factories["federation.Actor"](local=True)
    follow = factories["federation.LibraryFollow"](
        actor=remote_actor, target__actor=local_actor
    )

    activity = list(routes.outbox_reject_follow({"follow": follow}))[0]

    serializer = serializers.RejectFollowSerializer(
        follow, context={"actor": local_actor}
    )
    expected = serializer.data
    expected["to"] = [remote_actor]

    assert activity["payload"] == expected
    assert activity["actor"] == local_actor
    assert activity["object"] == follow
    assert activity["related_object"] == follow.target


def test_handle_library_entry_update_can_manage(factories, mocker):
    update_library_entity = mocker.patch(
        "funkwhale_api.music.tasks.update_library_entity"
    )
    activity = factories["federation.Activity"]()
    obj = factories["music.Artist"]()
    actor = factories["federation.Actor"]()
    mocker.patch.object(actor, "can_manage", return_value=False)
    data = serializers.ArtistSerializer(obj).data
    data["name"] = "New name"
    payload = {"type": "Update", "actor": actor, "object": data}

    routes.inbox_update_artist(
        payload, context={"actor": actor, "raise_exception": True, "activity": activity}
    )

    update_library_entity.assert_not_called()


def test_inbox_update_artist(factories, mocker):
    update_library_entity = mocker.patch(
        "funkwhale_api.music.tasks.update_library_entity"
    )
    activity = factories["federation.Activity"]()
    obj = factories["music.Artist"](attributed=True, attachment_cover=None)
    actor = obj.attributed_to
    data = serializers.ArtistSerializer(obj).data
    data["name"] = "New name"
    payload = {"type": "Update", "actor": actor, "object": data}

    routes.inbox_update_artist(
        payload, context={"actor": actor, "raise_exception": True, "activity": activity}
    )

    update_library_entity.assert_called_once_with(obj, {"name": "New name"})


def test_outbox_update_artist(factories):
    artist = factories["music.Artist"]()
    activity = list(routes.outbox_update_artist({"artist": artist}))[0]
    expected = serializers.ActivitySerializer(
        {"type": "Update", "object": serializers.ArtistSerializer(artist).data}
    ).data

    expected["to"] = [contexts.AS.Public, {"type": "instances_with_followers"}]

    assert dict(activity["payload"]) == dict(expected)
    assert activity["actor"] == actors.get_service_actor()


def test_inbox_update_album(factories, mocker):
    update_library_entity = mocker.patch(
        "funkwhale_api.music.tasks.update_library_entity"
    )
    activity = factories["federation.Activity"]()
    obj = factories["music.Album"](attributed=True, attachment_cover=None)
    actor = obj.attributed_to
    data = serializers.AlbumSerializer(obj).data
    data["name"] = "New title"
    payload = {"type": "Update", "actor": actor, "object": data}

    routes.inbox_update_album(
        payload, context={"actor": actor, "raise_exception": True, "activity": activity}
    )

    update_library_entity.assert_called_once_with(obj, {"title": "New title"})


def test_outbox_update_album(factories):
    album = factories["music.Album"]()
    activity = list(routes.outbox_update_album({"album": album}))[0]
    expected = serializers.ActivitySerializer(
        {"type": "Update", "object": serializers.AlbumSerializer(album).data}
    ).data

    expected["to"] = [contexts.AS.Public, {"type": "instances_with_followers"}]

    assert dict(activity["payload"]) == dict(expected)
    assert activity["actor"] == actors.get_service_actor()


def test_inbox_update_track(factories, mocker):
    update_library_entity = mocker.patch(
        "funkwhale_api.music.tasks.update_library_entity"
    )
    activity = factories["federation.Activity"]()
    obj = factories["music.Track"](attributed=True, attachment_cover=None)
    actor = obj.attributed_to
    data = serializers.TrackSerializer(obj).data
    data["name"] = "New title"
    payload = {"type": "Update", "actor": actor, "object": data}

    routes.inbox_update_track(
        payload, context={"actor": actor, "raise_exception": True, "activity": activity}
    )

    update_library_entity.assert_called_once_with(obj, {"title": "New title"})


def test_inbox_update_audio(factories, mocker, r_mock):
    channel = factories["audio.Channel"]()
    upload = factories["music.Upload"](
        library=channel.library,
        track__artist=channel.artist,
        track__attributed_to=channel.actor,
    )
    upload.track.fid = upload.fid
    upload.track.save()
    r_mock.get(
        upload.track.album.fid,
        json=serializers.AlbumSerializer(upload.track.album).data,
    )
    data = serializers.ChannelCreateUploadSerializer(upload).data
    data["object"]["name"] = "New title"

    routes.inbox_update_audio(
        data, context={"actor": channel.actor, "raise_exception": True}
    )

    upload.track.refresh_from_db()

    assert upload.track.title == "New title"


def test_outbox_update_audio(factories, faker, mocker):
    fake_uuid = faker.uuid4()
    mocker.patch("uuid.uuid4", return_value=fake_uuid)
    upload = factories["music.Upload"](channel=True)
    activity = list(routes.outbox_update_audio({"upload": upload}))[0]
    expected = serializers.ChannelCreateUploadSerializer(upload).data

    expected["type"] = "Update"
    expected["id"] += "/" + fake_uuid[:8]
    expected["to"] = [contexts.AS.Public, {"type": "instances_with_followers"}]

    assert dict(activity["payload"]) == dict(expected)
    assert activity["actor"] == upload.library.channel.actor


def test_outbox_update_track(factories):
    track = factories["music.Track"]()
    activity = list(routes.outbox_update_track({"track": track}))[0]
    expected = serializers.ActivitySerializer(
        {"type": "Update", "object": serializers.TrackSerializer(track).data}
    ).data

    expected["to"] = [contexts.AS.Public, {"type": "instances_with_followers"}]

    assert dict(activity["payload"]) == dict(expected)
    assert activity["actor"] == actors.get_service_actor()


def test_outbox_delete_actor(factories):
    user = factories["users.User"]()
    actor = user.create_actor()

    activity = list(routes.outbox_delete_actor({"actor": actor}))[0]
    expected = serializers.ActivitySerializer(
        {"type": "Delete", "object": {"id": actor.fid, "type": actor.type}}
    ).data

    expected["to"] = [contexts.AS.Public, {"type": "instances_with_followers"}]

    assert dict(activity["payload"]) == dict(expected)
    assert activity["actor"] == actor


def test_inbox_delete_actor(factories):
    remote_actor = factories["federation.Actor"]()
    serializer = serializers.ActivitySerializer(
        {
            "type": "Delete",
            "object": {"type": remote_actor.type, "id": remote_actor.fid},
        }
    )
    routes.inbox_delete_actor(
        serializer.data, context={"actor": remote_actor, "raise_exception": True}
    )
    with pytest.raises(remote_actor.__class__.DoesNotExist):
        remote_actor.refresh_from_db()


def test_inbox_delete_actor_only_works_on_self(factories):
    remote_actor1 = factories["federation.Actor"]()
    remote_actor2 = factories["federation.Actor"]()
    serializer = serializers.ActivitySerializer(
        {
            "type": "Delete",
            "object": {"type": remote_actor2.type, "id": remote_actor2.fid},
        }
    )
    routes.inbox_delete_actor(
        serializer.data, context={"actor": remote_actor1, "raise_exception": True}
    )
    remote_actor2.refresh_from_db()


def test_inbox_delete_actor_doesnt_delete_local_actor(factories):
    local_actor = factories["users.User"]().create_actor()
    serializer = serializers.ActivitySerializer(
        {"type": "Delete", "object": {"type": local_actor.type, "id": local_actor.fid}}
    )
    routes.inbox_delete_actor(
        serializer.data, context={"actor": local_actor, "raise_exception": True}
    )
    # actor should still be here!
    local_actor.refresh_from_db()


@pytest.mark.parametrize(
    "factory_name, factory_kwargs",
    [
        ("audio.Channel", {"local": True}),
        ("federation.Actor", {"local": True}),
        ("music.Artist", {"local": True}),
        ("music.Album", {"local": True}),
        ("music.Track", {"local": True}),
        ("music.Library", {"local": True}),
    ],
)
def test_inbox_flag(factory_name, factory_kwargs, factories, mocker):
    report_created_send = mocker.patch(
        "funkwhale_api.moderation.signals.report_created.send"
    )
    actor = factories["federation.Actor"]()
    target = factories[factory_name](**factory_kwargs)
    payload = {
        "type": "Flag",
        "object": [target.fid],
        "content": "Test report",
        "id": "https://" + actor.domain_id + "/testid",
        "actor": actor.fid,
    }
    serializer = serializers.ActivitySerializer(payload)

    result = routes.inbox_flag(
        serializer.data, context={"actor": actor, "raise_exception": True}
    )

    report = actor.reports.latest("id")

    assert result == {"object": target, "related_object": report}
    assert report.fid == payload["id"]
    assert report.type == "other"
    assert report.target == target
    assert report.target_owner == moderation_serializers.get_target_owner(target)
    assert report.target_state == moderation_serializers.get_target_state(target)

    report_created_send.assert_called_once_with(sender=None, report=report)


@pytest.mark.parametrize(
    "factory_name, factory_kwargs",
    [
        ("audio.Channel", {"local": True}),
        ("federation.Actor", {"local": True}),
        ("music.Artist", {"local": True}),
        ("music.Album", {"local": True}),
        ("music.Track", {"local": True}),
        ("music.Library", {"local": True}),
    ],
)
def test_outbox_flag(factory_name, factory_kwargs, factories, mocker):
    target = factories[factory_name](**factory_kwargs)
    report = factories["moderation.Report"](
        target=target, local=True, target_owner=factories["federation.Actor"]()
    )

    activity = list(routes.outbox_flag({"report": report}))[0]

    serializer = serializers.FlagSerializer(report)
    expected = serializer.data
    expected["to"] = [{"type": "actor_inbox", "actor": report.target_owner}]
    assert activity["payload"] == expected
    assert activity["actor"] == actors.get_service_actor()

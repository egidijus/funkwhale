import datetime

import pytest

from django.urls import reverse

from funkwhale_api.federation import api_serializers
from funkwhale_api.federation import serializers
from funkwhale_api.federation import tasks
from funkwhale_api.federation import views


def test_user_can_list_their_library_follows(factories, logged_in_api_client):
    # followed by someont else
    factories["federation.LibraryFollow"]()
    follow = factories["federation.LibraryFollow"](
        actor__user=logged_in_api_client.user
    )
    url = reverse("api:v1:federation:library-follows-list")
    response = logged_in_api_client.get(url)

    assert response.data["count"] == 1
    assert response.data["results"][0]["uuid"] == str(follow.uuid)


def test_user_can_fetch_library_using_url(mocker, factories, logged_in_api_client):
    library = factories["music.Library"]()
    mocked_retrieve = mocker.patch(
        "funkwhale_api.federation.utils.retrieve_ap_object", return_value=library
    )
    url = reverse("api:v1:federation:libraries-fetch")
    response = logged_in_api_client.post(url, {"fid": library.fid})
    assert mocked_retrieve.call_count == 1
    args = mocked_retrieve.call_args
    assert args[0] == (library.fid,)
    assert args[1]["queryset"].model == views.MusicLibraryViewSet.queryset.model
    assert args[1]["serializer_class"] == serializers.LibrarySerializer
    assert response.status_code == 200
    assert response.data["results"] == [api_serializers.LibrarySerializer(library).data]


def test_user_can_schedule_library_scan(mocker, factories, logged_in_api_client):
    actor = logged_in_api_client.user.create_actor()
    library = factories["music.Library"](privacy_level="everyone")

    schedule_scan = mocker.patch(
        "funkwhale_api.music.models.Library.schedule_scan", return_value=True
    )
    url = reverse("api:v1:federation:libraries-scan", kwargs={"uuid": library.uuid})

    response = logged_in_api_client.post(url)

    assert response.status_code == 200

    schedule_scan.assert_called_once_with(actor=actor)


def test_can_follow_library(factories, logged_in_api_client, mocker):
    dispatch = mocker.patch("funkwhale_api.federation.routes.outbox.dispatch")
    actor = logged_in_api_client.user.create_actor()
    library = factories["music.Library"]()
    url = reverse("api:v1:federation:library-follows-list")
    response = logged_in_api_client.post(url, {"target": library.uuid})

    assert response.status_code == 201

    follow = library.received_follows.latest("id")

    assert follow.approved is None
    assert follow.actor == actor

    dispatch.assert_called_once_with({"type": "Follow"}, context={"follow": follow})


def test_can_undo_library_follow(factories, logged_in_api_client, mocker):
    dispatch = mocker.patch("funkwhale_api.federation.routes.outbox.dispatch")
    actor = logged_in_api_client.user.create_actor()
    follow = factories["federation.LibraryFollow"](actor=actor)
    delete = mocker.patch.object(follow.__class__, "delete")
    url = reverse(
        "api:v1:federation:library-follows-detail", kwargs={"uuid": follow.uuid}
    )
    response = logged_in_api_client.delete(url)

    assert response.status_code == 204

    delete.assert_called_once_with()
    dispatch.assert_called_once_with(
        {"type": "Undo", "object": {"type": "Follow"}}, context={"follow": follow}
    )


@pytest.mark.parametrize("action", ["accept", "reject"])
def test_user_cannot_edit_someone_else_library_follow(
    factories, logged_in_api_client, action
):
    logged_in_api_client.user.create_actor()
    follow = factories["federation.LibraryFollow"]()
    url = reverse(
        "api:v1:federation:library-follows-{}".format(action),
        kwargs={"uuid": follow.uuid},
    )
    response = logged_in_api_client.post(url)

    assert response.status_code == 404


@pytest.mark.parametrize("action,expected", [("accept", True), ("reject", False)])
def test_user_can_accept_or_reject_own_follows(
    factories, logged_in_api_client, action, expected, mocker
):
    mocked_dispatch = mocker.patch(
        "funkwhale_api.federation.activity.OutboxRouter.dispatch"
    )
    actor = logged_in_api_client.user.create_actor()
    follow = factories["federation.LibraryFollow"](target__actor=actor)
    url = reverse(
        "api:v1:federation:library-follows-{}".format(action),
        kwargs={"uuid": follow.uuid},
    )
    response = logged_in_api_client.post(url)

    assert response.status_code == 204

    follow.refresh_from_db()

    assert follow.approved is expected

    mocked_dispatch.assert_called_once_with(
        {"type": action.title()}, context={"follow": follow}
    )


def test_user_can_list_inbox_items(factories, logged_in_api_client):
    actor = logged_in_api_client.user.create_actor()
    ii = factories["federation.InboxItem"](
        activity__type="Follow", actor=actor, type="to"
    )

    factories["federation.InboxItem"](activity__type="Follow", actor=actor, type="cc")
    factories["federation.InboxItem"](activity__type="Follow", type="to")

    url = reverse("api:v1:federation:inbox-list")

    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert response.data == {
        "count": 1,
        "results": [api_serializers.InboxItemSerializer(ii).data],
        "next": None,
        "previous": None,
    }


def test_user_can_update_read_status_of_inbox_item(factories, logged_in_api_client):
    actor = logged_in_api_client.user.create_actor()
    ii = factories["federation.InboxItem"](
        activity__type="Follow", actor=actor, type="to"
    )

    url = reverse("api:v1:federation:inbox-detail", kwargs={"pk": ii.pk})

    response = logged_in_api_client.patch(url, {"is_read": True})
    assert response.status_code == 200

    ii.refresh_from_db()

    assert ii.is_read is True


def test_can_detail_fetch(logged_in_api_client, factories):
    actor = logged_in_api_client.user.create_actor()
    fetch = factories["federation.Fetch"](url="http://test.object", actor=actor)
    url = reverse("api:v1:federation:fetches-detail", kwargs={"pk": fetch.pk})

    response = logged_in_api_client.get(url)

    expected = api_serializers.FetchSerializer(fetch).data

    assert response.status_code == 200
    assert response.data == expected


def test_user_can_list_domains(factories, api_client, preferences):
    preferences["common__api_authentication_required"] = False
    allowed = factories["federation.Domain"]()
    factories["moderation.InstancePolicy"](
        actor=None, for_domain=True, block_all=True
    ).target_domain
    url = reverse("api:v1:federation:domains-list")
    response = api_client.get(url)

    expected = {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [api_serializers.DomainSerializer(allowed).data],
    }
    assert response.data == expected


def test_can_retrieve_actor(factories, api_client, preferences):
    preferences["common__api_authentication_required"] = False
    actor = factories["federation.Actor"]()
    url = reverse(
        "api:v1:federation:actors-detail", kwargs={"full_username": actor.full_username}
    )
    response = api_client.get(url)

    expected = api_serializers.FullActorSerializer(actor).data
    assert response.data == expected


def test_can_retrieve_local_actor_with_allow_list_enabled(
    factories, api_client, preferences
):
    preferences["common__api_authentication_required"] = False
    preferences["moderation__allow_list_enabled"] = True
    actor = factories["federation.Actor"](local=True)
    url = reverse(
        "api:v1:federation:actors-detail", kwargs={"full_username": actor.full_username}
    )
    response = api_client.get(url)

    expected = api_serializers.FullActorSerializer(actor).data
    assert response.data == expected


@pytest.mark.parametrize(
    "object_id, expected_url",
    [
        ("https://fetch.url", "https://fetch.url"),
        ("name@domain.tld", "webfinger://name@domain.tld"),
        ("@name@domain.tld", "webfinger://name@domain.tld"),
    ],
)
def test_can_fetch_using_url_synchronous(
    object_id, expected_url, factories, logged_in_api_client, mocker, settings
):
    settings.FEDERATION_SYNCHRONOUS_FETCH = True
    actor = logged_in_api_client.user.create_actor()

    def fake_task(fetch_id):
        actor.fetches.filter(id=fetch_id).update(status="finished")

    fetch_task = mocker.patch.object(tasks, "fetch", side_effect=fake_task)

    url = reverse("api:v1:federation:fetches-list")
    data = {"object": object_id}
    response = logged_in_api_client.post(url, data)
    assert response.status_code == 201

    fetch = actor.fetches.latest("id")

    assert fetch.status == "finished"
    assert fetch.url == expected_url
    assert response.data == api_serializers.FetchSerializer(fetch).data
    fetch_task.assert_called_once_with(fetch_id=fetch.pk)


def test_fetch_duplicate(factories, logged_in_api_client, settings, now):
    object_id = "http://example.test"
    settings.FEDERATION_DUPLICATE_FETCH_DELAY = 60
    actor = logged_in_api_client.user.create_actor()
    duplicate = factories["federation.Fetch"](
        actor=actor,
        status="finished",
        url=object_id,
        creation_date=now - datetime.timedelta(seconds=59),
    )
    url = reverse("api:v1:federation:fetches-list")
    data = {"object": object_id}
    response = logged_in_api_client.post(url, data)
    assert response.status_code == 201
    assert response.data == api_serializers.FetchSerializer(duplicate).data


def test_fetch_duplicate_bypass_with_force(
    factories, logged_in_api_client, mocker, settings, now
):
    fetch_task = mocker.patch.object(tasks, "fetch")
    object_id = "http://example.test"
    settings.FEDERATION_DUPLICATE_FETCH_DELAY = 60
    actor = logged_in_api_client.user.create_actor()
    duplicate = factories["federation.Fetch"](
        actor=actor,
        status="finished",
        url=object_id,
        creation_date=now - datetime.timedelta(seconds=59),
    )
    url = reverse("api:v1:federation:fetches-list")
    data = {"object": object_id, "force": True}
    response = logged_in_api_client.post(url, data)

    fetch = actor.fetches.latest("id")
    assert fetch != duplicate
    assert response.status_code == 201
    assert response.data == api_serializers.FetchSerializer(fetch).data
    fetch_task.assert_called_once_with(fetch_id=fetch.pk)


def test_library_follow_get_all(factories, logged_in_api_client):
    actor = logged_in_api_client.user.create_actor()
    library = factories["music.Library"]()
    follow = factories["federation.LibraryFollow"](target=library, actor=actor)
    factories["federation.LibraryFollow"]()
    factories["music.Library"]()
    url = reverse("api:v1:federation:library-follows-all")
    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert response.data == {
        "results": [
            {
                "uuid": str(follow.uuid),
                "library": str(library.uuid),
                "approved": follow.approved,
            }
        ],
        "count": 1,
    }

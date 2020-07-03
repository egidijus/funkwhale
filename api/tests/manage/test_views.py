from django.urls import reverse

from funkwhale_api.federation import models as federation_models
from funkwhale_api.federation import tasks as federation_tasks
from funkwhale_api.manage import serializers
from funkwhale_api.moderation import tasks as moderation_tasks


def test_user_view(factories, superuser_api_client, mocker):
    mocker.patch("funkwhale_api.users.models.User.record_activity")
    users = factories["users.User"].create_batch(size=5) + [superuser_api_client.user]
    qs = users[0].__class__.objects.order_by("-id")
    url = reverse("api:v1:manage:users:users-list")

    response = superuser_api_client.get(url, {"sort": "-id"})
    expected = serializers.ManageUserSerializer(
        qs, many=True, context={"request": response.wsgi_request}
    ).data

    assert response.data["count"] == len(users)
    assert response.data["results"] == expected


def test_invitation_view(factories, superuser_api_client, mocker):
    invitations = factories["users.Invitation"].create_batch(size=5)
    qs = invitations[0].__class__.objects.order_by("-id")
    url = reverse("api:v1:manage:users:invitations-list")

    response = superuser_api_client.get(url, {"sort": "-id"})
    expected = serializers.ManageInvitationSerializer(qs, many=True).data

    assert response.data["count"] == len(invitations)
    assert response.data["results"] == expected


def test_invitation_view_create(factories, superuser_api_client, mocker):
    url = reverse("api:v1:manage:users:invitations-list")
    response = superuser_api_client.post(url)

    assert response.status_code == 201
    assert superuser_api_client.user.invitations.latest("id") is not None


def test_domain_list(factories, superuser_api_client, settings):
    factories["federation.Domain"](pk=settings.FEDERATION_HOSTNAME)
    d = factories["federation.Domain"]()
    url = reverse("api:v1:manage:federation:domains-list")
    response = superuser_api_client.get(url)

    assert response.status_code == 200

    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == d.pk


def test_domain_detail(factories, superuser_api_client):
    d = factories["federation.Domain"]()
    url = reverse("api:v1:manage:federation:domains-detail", kwargs={"pk": d.name})
    response = superuser_api_client.get(url)

    assert response.status_code == 200
    assert response.data["name"] == d.pk


def test_domain_create(superuser_api_client, mocker):
    update_domain_nodeinfo = mocker.patch(
        "funkwhale_api.federation.tasks.update_domain_nodeinfo"
    )
    url = reverse("api:v1:manage:federation:domains-list")
    response = superuser_api_client.post(url, {"name": "test.domain"})

    assert response.status_code == 201
    assert federation_models.Domain.objects.filter(pk="test.domain").exists()
    update_domain_nodeinfo.assert_called_once_with(domain_name="test.domain")


def test_domain_update_allowed(superuser_api_client, factories):
    domain = factories["federation.Domain"]()
    url = reverse("api:v1:manage:federation:domains-detail", kwargs={"pk": domain.name})
    response = superuser_api_client.put(url, {"allowed": True})

    assert response.status_code == 200
    domain.refresh_from_db()
    assert domain.allowed is True


def test_domain_update_cannot_change_name(superuser_api_client, factories):
    superuser_api_client.user.create_actor()

    domain = factories["federation.Domain"]()
    old_name = domain.name
    url = reverse("api:v1:manage:federation:domains-detail", kwargs={"pk": old_name})
    response = superuser_api_client.put(url, {"name": "something.else"})

    domain.refresh_from_db()

    assert response.status_code == 200
    assert domain.name == old_name
    # changing the pk of a model and saving results in a new DB entry in django,
    # so we check that no other entry was created
    assert (
        domain.__class__.objects.count() == 2
    )  # one for pod domain, and the other one


def test_domain_nodeinfo(factories, superuser_api_client, mocker):
    domain = factories["federation.Domain"]()
    url = reverse(
        "api:v1:manage:federation:domains-nodeinfo", kwargs={"pk": domain.name}
    )
    mocker.patch.object(
        federation_tasks, "fetch_nodeinfo", return_value={"hello": "world"}
    )
    update_domain_nodeinfo = mocker.spy(federation_tasks, "update_domain_nodeinfo")
    response = superuser_api_client.get(url)
    assert response.status_code == 200
    assert response.data == {"status": "ok", "payload": {"hello": "world"}}

    update_domain_nodeinfo.assert_called_once_with(domain_name=domain.name)


def test_domain_stats(factories, superuser_api_client, mocker):
    domain = factories["federation.Domain"]()
    mocker.patch.object(domain.__class__, "get_stats", return_value={"hello": "world"})
    url = reverse("api:v1:manage:federation:domains-stats", kwargs={"pk": domain.name})
    response = superuser_api_client.get(url)
    assert response.status_code == 200
    assert response.data == {"hello": "world"}


def test_actor_list(factories, superuser_api_client, settings):
    actor = factories["federation.Actor"]()
    url = reverse("api:v1:manage:accounts-list")
    response = superuser_api_client.get(url)

    assert response.status_code == 200

    assert response.data["count"] == 2
    assert response.data["results"][1]["id"] == actor.id


def test_actor_detail(factories, superuser_api_client):
    actor = factories["federation.Actor"]()
    url = reverse("api:v1:manage:accounts-detail", kwargs={"pk": actor.full_username})
    response = superuser_api_client.get(url)

    assert response.status_code == 200
    assert response.data["id"] == actor.id


def test_instance_policy_create(superuser_api_client, factories):
    domain = factories["federation.Domain"]()
    actor = superuser_api_client.user.create_actor()
    url = reverse("api:v1:manage:moderation:instance-policies-list")
    response = superuser_api_client.post(
        url,
        {"target": {"type": "domain", "id": domain.name}, "block_all": True},
        format="json",
    )

    assert response.status_code == 201

    policy = domain.instance_policy
    assert policy.actor == actor


def test_artist_list(factories, superuser_api_client, settings):
    artist = factories["music.Artist"]()
    url = reverse("api:v1:manage:library:artists-list")
    response = superuser_api_client.get(url)

    assert response.status_code == 200

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == artist.id


def test_artist_detail(factories, superuser_api_client):
    artist = factories["music.Artist"]()
    url = reverse("api:v1:manage:library:artists-detail", kwargs={"pk": artist.pk})
    response = superuser_api_client.get(url)

    assert response.status_code == 200
    assert response.data["id"] == artist.id


def test_artist_detail_stats(factories, superuser_api_client):
    artist = factories["music.Artist"]()
    url = reverse("api:v1:manage:library:artists-stats", kwargs={"pk": artist.pk})
    response = superuser_api_client.get(url)
    expected = {
        "libraries": 0,
        "channels": 0,
        "uploads": 0,
        "listenings": 0,
        "playlists": 0,
        "mutations": 0,
        "reports": 0,
        "track_favorites": 0,
        "media_total_size": 0,
        "media_downloaded_size": 0,
    }
    assert response.status_code == 200
    assert response.data == expected


def test_artist_delete(factories, superuser_api_client):
    artist = factories["music.Artist"]()
    url = reverse("api:v1:manage:library:artists-detail", kwargs={"pk": artist.pk})
    response = superuser_api_client.delete(url)

    assert response.status_code == 204


def test_album_list(factories, superuser_api_client, settings):
    album = factories["music.Album"]()
    factories["music.Album"]()
    url = reverse("api:v1:manage:library:albums-list")
    response = superuser_api_client.get(
        url, {"q": 'artist:"{}"'.format(album.artist.name)}
    )

    assert response.status_code == 200

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == album.id


def test_album_detail(factories, superuser_api_client):
    album = factories["music.Album"]()
    url = reverse("api:v1:manage:library:albums-detail", kwargs={"pk": album.pk})
    response = superuser_api_client.get(url)

    assert response.status_code == 200
    assert response.data["id"] == album.id


def test_album_detail_stats(factories, superuser_api_client):
    album = factories["music.Album"]()
    url = reverse("api:v1:manage:library:albums-stats", kwargs={"pk": album.pk})
    response = superuser_api_client.get(url)
    expected = {
        "libraries": 0,
        "channels": 0,
        "uploads": 0,
        "listenings": 0,
        "playlists": 0,
        "mutations": 0,
        "reports": 0,
        "track_favorites": 0,
        "media_total_size": 0,
        "media_downloaded_size": 0,
    }
    assert response.status_code == 200
    assert response.data == expected


def test_album_delete(factories, superuser_api_client):
    album = factories["music.Album"]()
    url = reverse("api:v1:manage:library:albums-detail", kwargs={"pk": album.pk})
    response = superuser_api_client.delete(url)

    assert response.status_code == 204


def test_track_list(factories, superuser_api_client, settings):
    track = factories["music.Track"]()
    url = reverse("api:v1:manage:library:tracks-list")
    response = superuser_api_client.get(url)

    assert response.status_code == 200

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == track.id


def test_track_detail(factories, superuser_api_client):
    track = factories["music.Track"]()
    url = reverse("api:v1:manage:library:tracks-detail", kwargs={"pk": track.pk})
    response = superuser_api_client.get(url)

    assert response.status_code == 200
    assert response.data["id"] == track.id


def test_track_detail_stats(factories, superuser_api_client):
    track = factories["music.Track"]()
    url = reverse("api:v1:manage:library:tracks-stats", kwargs={"pk": track.pk})
    response = superuser_api_client.get(url)
    expected = {
        "libraries": 0,
        "channels": 0,
        "uploads": 0,
        "listenings": 0,
        "playlists": 0,
        "mutations": 0,
        "reports": 0,
        "track_favorites": 0,
        "media_total_size": 0,
        "media_downloaded_size": 0,
    }
    assert response.status_code == 200
    assert response.data == expected


def test_track_delete(factories, superuser_api_client):
    track = factories["music.Track"]()
    url = reverse("api:v1:manage:library:tracks-detail", kwargs={"pk": track.pk})
    response = superuser_api_client.delete(url)

    assert response.status_code == 204


def test_library_list(factories, superuser_api_client, settings):
    library = factories["music.Library"]()
    url = reverse("api:v1:manage:library:libraries-list")
    response = superuser_api_client.get(url)

    assert response.status_code == 200

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == library.id


def test_library_list_exclude_channel_libraries(
    factories, superuser_api_client, settings
):
    factories["audio.Channel"]()
    url = reverse("api:v1:manage:library:libraries-list")
    response = superuser_api_client.get(url)

    assert response.status_code == 200
    assert response.data["count"] == 0


def test_library_detail(factories, superuser_api_client):
    library = factories["music.Library"]()
    url = reverse(
        "api:v1:manage:library:libraries-detail", kwargs={"uuid": library.uuid}
    )
    response = superuser_api_client.get(url)

    assert response.status_code == 200
    assert response.data["id"] == library.id


def test_library_update(factories, superuser_api_client):
    library = factories["music.Library"](privacy_level="everyone")
    url = reverse(
        "api:v1:manage:library:libraries-detail", kwargs={"uuid": library.uuid}
    )
    response = superuser_api_client.patch(url, {"privacy_level": "me"})

    assert response.status_code == 200
    library.refresh_from_db()
    assert library.privacy_level == "me"


def test_library_detail_stats(factories, superuser_api_client):
    library = factories["music.Library"]()
    url = reverse(
        "api:v1:manage:library:libraries-stats", kwargs={"uuid": library.uuid}
    )
    response = superuser_api_client.get(url)
    expected = {
        "uploads": 0,
        "followers": 0,
        "tracks": 0,
        "albums": 0,
        "artists": 0,
        "reports": 0,
        "media_total_size": 0,
        "media_downloaded_size": 0,
    }
    assert response.status_code == 200
    assert response.data == expected


def test_library_delete(factories, superuser_api_client):
    library = factories["music.Library"]()
    url = reverse(
        "api:v1:manage:library:libraries-detail", kwargs={"uuid": library.uuid}
    )
    response = superuser_api_client.delete(url)

    assert response.status_code == 204


def test_upload_list(factories, superuser_api_client, settings):
    upload = factories["music.Upload"]()
    url = reverse("api:v1:manage:library:uploads-list")
    response = superuser_api_client.get(url)

    assert response.status_code == 200

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == upload.id


def test_upload_detail(factories, superuser_api_client):
    upload = factories["music.Upload"]()
    url = reverse("api:v1:manage:library:uploads-detail", kwargs={"uuid": upload.uuid})
    response = superuser_api_client.get(url)

    assert response.status_code == 200
    assert response.data["id"] == upload.id


def test_upload_delete(factories, superuser_api_client):
    upload = factories["music.Upload"]()
    url = reverse("api:v1:manage:library:uploads-detail", kwargs={"uuid": upload.uuid})
    response = superuser_api_client.delete(url)

    assert response.status_code == 204


def test_note_create_actor(factories, superuser_api_client):
    actor = superuser_api_client.user.create_actor()
    target = factories["federation.Actor"]()
    data = {
        "summary": "Hello",
        "target": {"type": "account", "full_username": target.full_username},
    }
    url = reverse("api:v1:manage:moderation:notes-list")
    response = superuser_api_client.post(url, data, format="json")
    assert response.status_code == 201

    note = actor.moderation_notes.latest("id")
    assert note.target == target
    assert response.data == serializers.ManageNoteSerializer(note).data


def test_note_create_user_request(factories, superuser_api_client):
    actor = superuser_api_client.user.create_actor()
    target = factories["moderation.UserRequest"]()
    data = {
        "summary": "Hello",
        "target": {"type": "request", "uuid": target.uuid},
    }
    url = reverse("api:v1:manage:moderation:notes-list")
    response = superuser_api_client.post(url, data, format="json")
    assert response.status_code == 201

    note = actor.moderation_notes.latest("id")
    assert note.target == target
    assert response.data == serializers.ManageNoteSerializer(note).data


def test_note_list(factories, superuser_api_client, settings):
    note = factories["moderation.Note"]()
    url = reverse("api:v1:manage:moderation:notes-list")
    response = superuser_api_client.get(url)

    assert response.status_code == 200

    assert response.data["count"] == 1
    assert response.data["results"][0] == serializers.ManageNoteSerializer(note).data


def test_note_delete(factories, superuser_api_client):
    note = factories["moderation.Note"]()
    url = reverse("api:v1:manage:moderation:notes-detail", kwargs={"uuid": note.uuid})
    response = superuser_api_client.delete(url)

    assert response.status_code == 204


def test_note_detail(factories, superuser_api_client):
    note = factories["moderation.Note"]()
    url = reverse("api:v1:manage:moderation:notes-detail", kwargs={"uuid": note.uuid})
    response = superuser_api_client.get(url)

    assert response.status_code == 200
    assert response.data == serializers.ManageNoteSerializer(note).data


def test_tag_detail(factories, superuser_api_client):
    tag = factories["tags.Tag"]()
    url = reverse("api:v1:manage:tags-detail", kwargs={"name": tag.name})
    response = superuser_api_client.get(url)

    assert response.status_code == 200
    assert response.data["name"] == tag.name


def test_tag_list(factories, superuser_api_client, settings):
    tag = factories["tags.Tag"]()
    url = reverse("api:v1:manage:tags-list")
    response = superuser_api_client.get(url)

    assert response.status_code == 200

    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == tag.name


def test_tag_delete(factories, superuser_api_client):
    tag = factories["tags.Tag"]()
    url = reverse("api:v1:manage:tags-detail", kwargs={"name": tag.name})
    response = superuser_api_client.delete(url)

    assert response.status_code == 204


def test_report_detail(factories, superuser_api_client):
    report = factories["moderation.Report"]()
    url = reverse(
        "api:v1:manage:moderation:reports-detail", kwargs={"uuid": report.uuid}
    )
    response = superuser_api_client.get(url)

    assert response.status_code == 200
    assert response.data["summary"] == report.summary


def test_report_list(factories, superuser_api_client, settings):
    report = factories["moderation.Report"]()
    url = reverse("api:v1:manage:moderation:reports-list")
    response = superuser_api_client.get(url)

    assert response.status_code == 200

    assert response.data["count"] == 1
    assert response.data["results"][0]["summary"] == report.summary


def test_report_update(factories, superuser_api_client):
    report = factories["moderation.Report"]()
    url = reverse(
        "api:v1:manage:moderation:reports-detail", kwargs={"uuid": report.uuid}
    )
    response = superuser_api_client.patch(url, {"is_handled": True})

    assert response.status_code == 200
    report.refresh_from_db()
    assert report.is_handled is True


def test_report_update_is_handled_true_assigns(factories, superuser_api_client):
    actor = superuser_api_client.user.create_actor()
    report = factories["moderation.Report"]()
    url = reverse(
        "api:v1:manage:moderation:reports-detail", kwargs={"uuid": report.uuid}
    )
    response = superuser_api_client.patch(url, {"is_handled": True})

    assert response.status_code == 200
    report.refresh_from_db()
    assert report.is_handled is True
    assert report.assigned_to == actor


def test_request_detail(factories, superuser_api_client):
    request = factories["moderation.UserRequest"]()
    url = reverse(
        "api:v1:manage:moderation:requests-detail", kwargs={"uuid": request.uuid}
    )
    response = superuser_api_client.get(url)

    assert response.status_code == 200
    assert response.data["uuid"] == str(request.uuid)


def test_request_list(factories, superuser_api_client, settings):
    request = factories["moderation.UserRequest"]()
    url = reverse("api:v1:manage:moderation:requests-list")
    response = superuser_api_client.get(url)

    assert response.status_code == 200

    assert response.data["count"] == 1
    assert response.data["results"][0]["uuid"] == str(request.uuid)


def test_user_request_update(factories, superuser_api_client):
    user_request = factories["moderation.UserRequest"](signup=True)
    url = reverse(
        "api:v1:manage:moderation:requests-detail", kwargs={"uuid": user_request.uuid}
    )
    response = superuser_api_client.patch(url, {"status": "approved"})

    assert response.status_code == 200
    user_request.refresh_from_db()
    assert user_request.status == "approved"


def test_user_request_update_status_assigns(factories, superuser_api_client, mocker):
    actor = superuser_api_client.user.create_actor()
    user_request = factories["moderation.UserRequest"](signup=True)
    url = reverse(
        "api:v1:manage:moderation:requests-detail", kwargs={"uuid": user_request.uuid}
    )
    on_commit = mocker.patch("funkwhale_api.common.utils.on_commit")
    response = superuser_api_client.patch(url, {"status": "refused"})

    assert response.status_code == 200
    user_request.refresh_from_db()
    assert user_request.status == "refused"
    assert user_request.assigned_to == actor
    on_commit.assert_called_once_with(
        moderation_tasks.user_request_handle.delay,
        user_request_id=user_request.pk,
        new_status="refused",
        old_status="pending",
    )


def test_channel_list(factories, superuser_api_client, settings):
    channel = factories["audio.Channel"]()
    url = reverse("api:v1:manage:channels-list")
    response = superuser_api_client.get(url)

    assert response.status_code == 200

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == channel.id


def test_channel_detail(factories, superuser_api_client):
    channel = factories["audio.Channel"]()
    url = reverse("api:v1:manage:channels-detail", kwargs={"composite": channel.uuid})
    response = superuser_api_client.get(url)

    assert response.status_code == 200
    assert response.data["id"] == channel.id


def test_channel_delete(factories, superuser_api_client, mocker):
    channel = factories["audio.Channel"]()
    url = reverse("api:v1:manage:channels-detail", kwargs={"composite": channel.uuid})
    response = superuser_api_client.delete(url)

    assert response.status_code == 204


def test_channel_detail_stats(factories, superuser_api_client):
    channel = factories["audio.Channel"]()
    url = reverse("api:v1:manage:channels-stats", kwargs={"composite": channel.uuid})
    response = superuser_api_client.get(url)
    expected = {
        "uploads": 0,
        "playlists": 0,
        "listenings": 0,
        "mutations": 0,
        "reports": 0,
        "follows": 0,
        "track_favorites": 0,
        "media_total_size": 0,
        "media_downloaded_size": 0,
    }
    assert response.status_code == 200
    assert response.data == expected

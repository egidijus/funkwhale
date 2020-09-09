import pytest

from funkwhale_api.common import serializers as common_serializers
from funkwhale_api.federation import tasks as federation_tasks
from funkwhale_api.manage import serializers


def test_manage_upload_action_delete(factories):
    uploads = factories["music.Upload"](size=5)
    s = serializers.ManageUploadActionSerializer(queryset=None)

    s.handle_delete(uploads.__class__.objects.all())

    assert uploads.__class__.objects.count() == 0


def test_user_update_permission(factories):
    user = factories["users.User"](
        permission_library=False,
        permission_moderation=False,
        permission_settings=True,
        is_active=True,
    )
    s = serializers.ManageUserSerializer(
        user,
        data={
            "is_active": False,
            "permissions": {"moderation": True, "settings": False},
            "upload_quota": 12,
        },
    )
    s.is_valid(raise_exception=True)
    s.save()
    user.refresh_from_db()

    assert user.is_active is False
    assert user.upload_quota == 12
    assert user.permission_moderation is True
    assert user.permission_library is False
    assert user.permission_settings is False


def test_manage_domain_serializer(factories, now, to_api_date):
    domain = factories["federation.Domain"](nodeinfo_fetch_date=None)
    setattr(domain, "actors_count", 42)
    setattr(domain, "outbox_activities_count", 23)
    expected = {
        "name": domain.name,
        "creation_date": to_api_date(domain.creation_date),
        "actors_count": 42,
        "outbox_activities_count": 23,
        "nodeinfo": {},
        "nodeinfo_fetch_date": None,
        "instance_policy": None,
        "allowed": None,
    }
    s = serializers.ManageDomainSerializer(domain)

    assert s.data == expected


def test_manage_domain_serializer_validates_hostname(db):
    s = serializers.ManageDomainSerializer(data={"name": "hello world"})

    with pytest.raises(serializers.serializers.ValidationError):
        s.is_valid(raise_exception=True)


def test_manage_actor_serializer(factories, now, to_api_date):
    actor = factories["federation.Actor"]()
    setattr(actor, "uploads_count", 66)
    expected = {
        "id": actor.id,
        "name": actor.name,
        "creation_date": to_api_date(actor.creation_date),
        "last_fetch_date": to_api_date(actor.last_fetch_date),
        "uploads_count": 66,
        "fid": actor.fid,
        "url": actor.url,
        "outbox_url": actor.outbox_url,
        "shared_inbox_url": actor.shared_inbox_url,
        "inbox_url": actor.inbox_url,
        "domain": actor.domain_id,
        "type": actor.type,
        "summary": actor.summary,
        "preferred_username": actor.preferred_username,
        "manually_approves_followers": actor.manually_approves_followers,
        "full_username": actor.full_username,
        "user": None,
        "instance_policy": None,
        "is_local": False,
    }
    s = serializers.ManageActorSerializer(actor)

    assert s.data == expected


@pytest.mark.parametrize(
    "factory_kwargs,expected",
    [
        (
            {"for_domain": True, "target_domain__name": "test.federation"},
            {"target": {"type": "domain", "id": "test.federation"}},
        ),
        (
            {
                "for_actor": True,
                "target_actor__domain__name": "test.federation",
                "target_actor__preferred_username": "hello",
            },
            {"target": {"type": "actor", "id": "hello@test.federation"}},
        ),
    ],
)
def test_instance_policy_serializer_repr(
    factories, factory_kwargs, expected, to_api_date
):
    policy = factories["moderation.InstancePolicy"](block_all=True, **factory_kwargs)

    e = {
        "id": policy.id,
        "uuid": str(policy.uuid),
        "creation_date": to_api_date(policy.creation_date),
        "actor": policy.actor.full_username,
        "block_all": True,
        "silence_activity": False,
        "silence_notifications": False,
        "reject_media": False,
        "is_active": policy.is_active,
        "summary": policy.summary,
    }
    e.update(expected)

    assert serializers.ManageInstancePolicySerializer(policy).data == e


def test_instance_policy_serializer_save_domain(factories):
    domain = factories["federation.Domain"]()

    data = {"target": {"id": domain.name, "type": "domain"}, "block_all": True}

    serializer = serializers.ManageInstancePolicySerializer(data=data)
    serializer.is_valid(raise_exception=True)
    policy = serializer.save()

    assert policy.target_domain == domain


def test_instance_policy_serializer_save_actor(factories):
    actor = factories["federation.Actor"]()

    data = {"target": {"id": actor.full_username, "type": "actor"}, "block_all": True}

    serializer = serializers.ManageInstancePolicySerializer(data=data)
    serializer.is_valid(raise_exception=True)
    policy = serializer.save()

    assert policy.target_actor == actor


def test_manage_actor_action_purge(factories, mocker):
    actors = factories["federation.Actor"].create_batch(size=3)
    s = serializers.ManageActorActionSerializer(queryset=None)
    on_commit = mocker.patch("funkwhale_api.common.utils.on_commit")

    s.handle_purge(actors[0].__class__.objects.all())
    on_commit.assert_called_once_with(
        federation_tasks.purge_actors.delay, ids=[a.pk for a in actors]
    )


def test_manage_domain_action_purge(factories, mocker):
    domains = factories["federation.Domain"].create_batch(size=3)
    s = serializers.ManageDomainActionSerializer(queryset=None)
    on_commit = mocker.patch("funkwhale_api.common.utils.on_commit")

    s.handle_purge(domains[0].__class__.objects.all())
    on_commit.assert_called_once_with(
        federation_tasks.purge_actors.delay,
        domains=[d.pk for d in sorted(domains, key=lambda d: d.name)],
    )


def test_manage_domain_action_allow_list_add(factories, mocker):
    domains = factories["federation.Domain"].create_batch(size=3, allowed=False)
    s = serializers.ManageDomainActionSerializer(queryset=None)
    s.handle_allow_list_add(domains[0].__class__.objects.all())

    for domain in domains:
        domain.refresh_from_db()
        assert domain.allowed is True


def test_manage_domain_action_allow_list_remove(factories, mocker):
    domains = factories["federation.Domain"].create_batch(size=3, allowed=True)
    s = serializers.ManageDomainActionSerializer(queryset=None)
    s.handle_allow_list_remove(domains[0].__class__.objects.all())

    for domain in domains:
        domain.refresh_from_db()
        assert domain.allowed is False


@pytest.mark.parametrize(
    "param,expected_only", [("block_all", []), ("reject_media", ["media"])]
)
def test_instance_policy_serializer_purges_target_domain(
    factories, mocker, param, expected_only
):
    params = {param: False}
    if param != "block_all":
        params["block_all"] = False
    policy = factories["moderation.InstancePolicy"](for_domain=True, **params)
    on_commit = mocker.patch("funkwhale_api.common.utils.on_commit")

    serializer = serializers.ManageInstancePolicySerializer(
        policy, data={param: True}, partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    policy.refresh_from_db()

    assert getattr(policy, param) is True
    on_commit.assert_called_once_with(
        federation_tasks.purge_actors.delay,
        domains=[policy.target_domain_id],
        only=expected_only,
    )

    on_commit.reset_mock()

    # setting to false should have no effect
    serializer = serializers.ManageInstancePolicySerializer(
        policy, data={param: False}, partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    policy.refresh_from_db()

    assert getattr(policy, param) is False
    assert on_commit.call_count == 0


@pytest.mark.parametrize(
    "param,expected_only", [("block_all", []), ("reject_media", ["media"])]
)
def test_instance_policy_serializer_purges_target_actor(
    factories, mocker, param, expected_only
):
    params = {param: False}
    if param != "block_all":
        params["block_all"] = False
    policy = factories["moderation.InstancePolicy"](for_actor=True, **params)
    on_commit = mocker.patch("funkwhale_api.common.utils.on_commit")

    serializer = serializers.ManageInstancePolicySerializer(
        policy, data={param: True}, partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    policy.refresh_from_db()

    assert getattr(policy, param) is True
    on_commit.assert_called_once_with(
        federation_tasks.purge_actors.delay,
        ids=[policy.target_actor_id],
        only=expected_only,
    )

    on_commit.reset_mock()

    # setting to false should have no effect
    serializer = serializers.ManageInstancePolicySerializer(
        policy, data={param: False}, partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    policy.refresh_from_db()

    assert getattr(policy, param) is False
    assert on_commit.call_count == 0


def test_manage_artist_serializer(factories, now, to_api_date):
    artist = factories["music.Artist"](attributed=True, with_cover=True)
    channel = factories["audio.Channel"](artist=artist)
    # put channel in cache
    artist.get_channel()
    setattr(artist, "_tracks_count", 12)
    setattr(artist, "_albums_count", 13)
    expected = {
        "id": artist.id,
        "domain": artist.domain_name,
        "is_local": artist.is_local,
        "fid": artist.fid,
        "name": artist.name,
        "mbid": artist.mbid,
        "creation_date": to_api_date(artist.creation_date),
        "tracks_count": 12,
        "albums_count": 13,
        "attributed_to": serializers.ManageBaseActorSerializer(
            artist.attributed_to
        ).data,
        "tags": [],
        "channel": str(channel.uuid),
        "content_category": artist.content_category,
        "cover": common_serializers.AttachmentSerializer(artist.attachment_cover).data,
    }
    s = serializers.ManageArtistSerializer(artist)

    assert s.data == expected


def test_manage_nested_track_serializer(factories, now, to_api_date):
    track = factories["music.Track"]()
    expected = {
        "id": track.id,
        "domain": track.domain_name,
        "is_local": track.is_local,
        "fid": track.fid,
        "title": track.title,
        "mbid": track.mbid,
        "creation_date": to_api_date(track.creation_date),
        "position": track.position,
        "disc_number": track.disc_number,
        "copyright": track.copyright,
        "license": track.license,
    }
    s = serializers.ManageNestedTrackSerializer(track)

    assert s.data == expected


def test_manage_nested_album_serializer(factories, now, to_api_date):
    album = factories["music.Album"](with_cover=True)
    setattr(album, "tracks_count", 44)
    expected = {
        "id": album.id,
        "domain": album.domain_name,
        "is_local": album.is_local,
        "fid": album.fid,
        "title": album.title,
        "mbid": album.mbid,
        "creation_date": to_api_date(album.creation_date),
        "release_date": album.release_date.isoformat(),
        "cover": common_serializers.AttachmentSerializer(album.attachment_cover).data,
        "tracks_count": 44,
    }
    s = serializers.ManageNestedAlbumSerializer(album)

    assert s.data == expected


def test_manage_nested_artist_serializer(factories, now, to_api_date):
    artist = factories["music.Artist"]()
    expected = {
        "id": artist.id,
        "domain": artist.domain_name,
        "is_local": artist.is_local,
        "fid": artist.fid,
        "name": artist.name,
        "mbid": artist.mbid,
        "creation_date": to_api_date(artist.creation_date),
    }
    s = serializers.ManageNestedArtistSerializer(artist)

    assert s.data == expected


def test_manage_album_serializer(factories, now, to_api_date):
    album = factories["music.Album"](attributed=True, with_cover=True)
    factories["music.Track"](album=album)
    setattr(album, "_tracks_count", 42)
    expected = {
        "id": album.id,
        "domain": album.domain_name,
        "is_local": album.is_local,
        "fid": album.fid,
        "title": album.title,
        "mbid": album.mbid,
        "creation_date": to_api_date(album.creation_date),
        "release_date": album.release_date.isoformat(),
        "cover": common_serializers.AttachmentSerializer(album.attachment_cover).data,
        "artist": serializers.ManageNestedArtistSerializer(album.artist).data,
        "attributed_to": serializers.ManageBaseActorSerializer(
            album.attributed_to
        ).data,
        "tags": [],
        "tracks_count": 1,
    }
    s = serializers.ManageAlbumSerializer(album)

    assert s.data == expected


def test_manage_track_serializer(factories, now, to_api_date):
    track = factories["music.Track"](attributed=True, with_cover=True)
    setattr(track, "uploads_count", 44)
    expected = {
        "id": track.id,
        "domain": track.domain_name,
        "is_local": track.is_local,
        "fid": track.fid,
        "title": track.title,
        "mbid": track.mbid,
        "disc_number": track.disc_number,
        "position": track.position,
        "copyright": track.copyright,
        "license": track.license,
        "creation_date": to_api_date(track.creation_date),
        "artist": serializers.ManageNestedArtistSerializer(track.artist).data,
        "album": serializers.ManageTrackAlbumSerializer(track.album).data,
        "attributed_to": serializers.ManageBaseActorSerializer(
            track.attributed_to
        ).data,
        "uploads_count": 44,
        "tags": [],
        "cover": common_serializers.AttachmentSerializer(track.attachment_cover).data,
    }
    s = serializers.ManageTrackSerializer(track)

    assert s.data == expected


def test_manage_library_serializer(factories, now, to_api_date):
    library = factories["music.Library"]()
    setattr(library, "followers_count", 42)
    setattr(library, "_uploads_count", 44)
    expected = {
        "id": library.id,
        "fid": library.fid,
        "url": library.url,
        "uuid": str(library.uuid),
        "followers_url": library.followers_url,
        "domain": library.domain_name,
        "is_local": library.is_local,
        "name": library.name,
        "description": library.description,
        "privacy_level": library.privacy_level,
        "creation_date": to_api_date(library.creation_date),
        "actor": serializers.ManageBaseActorSerializer(library.actor).data,
        "uploads_count": 44,
        "followers_count": 42,
    }
    s = serializers.ManageLibrarySerializer(library)

    assert s.data == expected


def test_manage_upload_serializer(factories, now, to_api_date):
    upload = factories["music.Upload"]()

    expected = {
        "id": upload.id,
        "fid": upload.fid,
        "audio_file": upload.audio_file.url,
        "listen_url": upload.listen_url,
        "uuid": str(upload.uuid),
        "domain": upload.domain_name,
        "is_local": upload.is_local,
        "duration": upload.duration,
        "size": upload.size,
        "bitrate": upload.bitrate,
        "mimetype": upload.mimetype,
        "source": upload.source,
        "filename": upload.filename,
        "metadata": upload.metadata,
        "creation_date": to_api_date(upload.creation_date),
        "modification_date": to_api_date(upload.modification_date),
        "accessed_date": None,
        "import_date": None,
        "import_metadata": upload.import_metadata,
        "import_status": upload.import_status,
        "import_reference": upload.import_reference,
        "import_details": upload.import_details,
        "library": serializers.ManageNestedLibrarySerializer(upload.library).data,
        "track": serializers.ManageNestedTrackSerializer(upload.track).data,
    }
    s = serializers.ManageUploadSerializer(upload)

    assert s.data == expected


@pytest.mark.parametrize(
    "factory, serializer_class",
    [
        ("music.Track", serializers.ManageTrackActionSerializer),
        ("music.Album", serializers.ManageAlbumActionSerializer),
        ("music.Artist", serializers.ManageArtistActionSerializer),
        ("music.Library", serializers.ManageLibraryActionSerializer),
        ("music.Upload", serializers.ManageUploadActionSerializer),
        ("tags.Tag", serializers.ManageTagActionSerializer),
    ],
)
def test_action_serializer_delete(factory, serializer_class, factories):
    objects = factories[factory].create_batch(size=5)
    s = serializer_class(queryset=None)

    s.handle_delete(objects[0].__class__.objects.all())

    assert objects[0].__class__.objects.count() == 0


def test_manage_tag_serializer(factories, to_api_date):
    tag = factories["tags.Tag"]()

    setattr(tag, "_tracks_count", 42)
    setattr(tag, "_albums_count", 54)
    setattr(tag, "_artists_count", 66)
    expected = {
        "id": tag.id,
        "name": tag.name,
        "creation_date": to_api_date(tag.creation_date),
        "tracks_count": 42,
        "albums_count": 54,
        "artists_count": 66,
    }
    s = serializers.ManageTagSerializer(tag)

    assert s.data == expected


def test_manage_report_serializer(factories, to_api_date):
    artist = factories["music.Artist"](attributed=True)
    report = factories["moderation.Report"](
        target=artist, target_state={"hello": "world"}, assigned=True
    )
    expected = {
        "id": report.id,
        "uuid": str(report.uuid),
        "fid": report.fid,
        "creation_date": to_api_date(report.creation_date),
        "handled_date": None,
        "summary": report.summary,
        "is_handled": report.is_handled,
        "type": report.type,
        "submitter_email": None,
        "submitter": serializers.ManageBaseActorSerializer(report.submitter).data,
        "assigned_to": serializers.ManageBaseActorSerializer(report.assigned_to).data,
        "target": {"type": "artist", "id": artist.pk},
        "target_owner": serializers.ManageBaseActorSerializer(
            artist.attributed_to
        ).data,
        "target_state": report.target_state,
        "notes": [],
    }
    s = serializers.ManageReportSerializer(report)

    assert s.data == expected


def test_manage_note_serializer(factories, to_api_date):
    actor = factories["federation.Actor"]()
    note = factories["moderation.Note"](target=actor)

    expected = {
        "id": note.id,
        "uuid": str(note.uuid),
        "summary": note.summary,
        "creation_date": to_api_date(note.creation_date),
        "author": serializers.ManageBaseActorSerializer(note.author).data,
        "target": {"type": "account", "full_username": actor.full_username},
    }
    s = serializers.ManageNoteSerializer(note)

    assert s.data == expected


def test_manage_user_request_serializer(factories, to_api_date):
    user_request = factories["moderation.UserRequest"](
        signup=True, metadata={"foo": "bar"}, assigned=True
    )
    expected = {
        "id": user_request.id,
        "uuid": str(user_request.uuid),
        "creation_date": to_api_date(user_request.creation_date),
        "handled_date": None,
        "status": user_request.status,
        "type": user_request.type,
        "submitter": serializers.ManageBaseActorSerializer(user_request.submitter).data,
        "assigned_to": serializers.ManageBaseActorSerializer(
            user_request.assigned_to
        ).data,
        "metadata": {"foo": "bar"},
        "notes": [],
    }
    s = serializers.ManageUserRequestSerializer(user_request)

    assert s.data == expected


def test_manage_channel_serializer(factories, now, to_api_date):
    channel = factories["audio.Channel"]()
    expected = {
        "id": channel.id,
        "uuid": channel.uuid,
        "artist": serializers.ManageArtistSerializer(channel.artist).data,
        "actor": serializers.ManageBaseActorSerializer(channel.actor).data,
        "attributed_to": serializers.ManageBaseActorSerializer(
            channel.attributed_to
        ).data,
        "creation_date": to_api_date(channel.creation_date),
        "rss_url": channel.get_rss_url(),
        "metadata": channel.metadata,
    }
    s = serializers.ManageChannelSerializer(channel)

    assert s.data == expected

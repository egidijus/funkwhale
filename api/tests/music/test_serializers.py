import pytest
import uuid

from funkwhale_api.common import serializers as common_serializers
from funkwhale_api.federation import serializers as federation_serializers
from funkwhale_api.music import licenses
from funkwhale_api.music import models
from funkwhale_api.music import serializers
from funkwhale_api.music import tasks


def test_license_serializer():
    """
    We serializer all licenses to ensure we have valid hardcoded data
    """
    for data in licenses.LICENSES:
        expected = {
            "id": data["identifiers"][0],
            "code": data["code"],
            "name": data["name"],
            "url": data["url"],
            "redistribute": data["redistribute"],
            "derivative": data["derivative"],
            "commercial": data["commercial"],
            "attribution": data["attribution"],
            "copyleft": data["copyleft"],
        }

        serializer = serializers.LicenseSerializer(data)

        assert serializer.data == expected


def test_artist_album_serializer(factories, to_api_date):
    track = factories["music.Track"](album__with_cover=True)
    album = track.album
    album = album.__class__.objects.with_tracks_count().get(pk=album.pk)
    expected = {
        "id": album.id,
        "fid": album.fid,
        "mbid": str(album.mbid),
        "title": album.title,
        "artist": album.artist.id,
        "creation_date": to_api_date(album.creation_date),
        "tracks_count": 1,
        "is_playable": None,
        "cover": common_serializers.AttachmentSerializer(album.attachment_cover).data,
        "release_date": to_api_date(album.release_date),
        "is_local": album.is_local,
    }
    serializer = serializers.ArtistAlbumSerializer(album)

    assert serializer.data == expected


def test_artist_with_albums_serializer(factories, to_api_date):
    actor = factories["federation.Actor"]()
    track = factories["music.Track"](
        album__artist__attributed_to=actor, album__artist__with_cover=True
    )
    artist = track.artist
    artist = artist.__class__.objects.with_albums().get(pk=artist.pk)
    album = list(artist.albums.all())[0]
    setattr(artist, "_prefetched_tracks", range(42))
    expected = {
        "id": artist.id,
        "fid": artist.fid,
        "mbid": str(artist.mbid),
        "name": artist.name,
        "is_local": artist.is_local,
        "content_category": artist.content_category,
        "creation_date": to_api_date(artist.creation_date),
        "albums": [serializers.ArtistAlbumSerializer(album).data],
        "tags": [],
        "attributed_to": federation_serializers.APIActorSerializer(actor).data,
        "tracks_count": 42,
        "cover": common_serializers.AttachmentSerializer(artist.attachment_cover).data,
        "channel": None,
    }
    serializer = serializers.ArtistWithAlbumsSerializer(artist)
    assert serializer.data == expected


def test_artist_with_albums_serializer_channel(factories, to_api_date):
    actor = factories["federation.Actor"]()
    channel = factories["audio.Channel"](attributed_to=actor, artist__with_cover=True)
    track = factories["music.Track"](album__artist=channel.artist)
    artist = track.artist
    artist = artist.__class__.objects.with_albums().get(pk=artist.pk)
    album = list(artist.albums.all())[0]
    setattr(artist, "_prefetched_tracks", range(42))
    expected = {
        "id": artist.id,
        "fid": artist.fid,
        "mbid": str(artist.mbid),
        "name": artist.name,
        "is_local": artist.is_local,
        "content_category": artist.content_category,
        "creation_date": to_api_date(artist.creation_date),
        "albums": [serializers.ArtistAlbumSerializer(album).data],
        "tags": [],
        "attributed_to": federation_serializers.APIActorSerializer(actor).data,
        "tracks_count": 42,
        "cover": common_serializers.AttachmentSerializer(artist.attachment_cover).data,
        "channel": {
            "uuid": str(channel.uuid),
            "actor": {
                "full_username": channel.actor.full_username,
                "preferred_username": channel.actor.preferred_username,
                "domain": channel.actor.domain_id,
            },
        },
    }
    serializer = serializers.ArtistWithAlbumsSerializer(artist)
    assert serializer.data == expected


def test_upload_serializer(factories, to_api_date):
    upload = factories["music.Upload"]()

    expected = {
        "uuid": str(upload.uuid),
        "filename": upload.filename,
        "track": serializers.TrackSerializer(upload.track).data,
        "duration": upload.duration,
        "mimetype": upload.mimetype,
        "bitrate": upload.bitrate,
        "size": upload.size,
        "library": serializers.LibraryForOwnerSerializer(upload.library).data,
        "creation_date": to_api_date(upload.creation_date),
        "import_date": None,
        "import_status": "pending",
    }
    serializer = serializers.UploadSerializer(upload)
    assert serializer.data == expected


def test_upload_owner_serializer(factories, to_api_date):
    upload = factories["music.Upload"](
        import_status="success",
        import_details={"hello": "world"},
        import_metadata={"import": "metadata"},
        import_reference="ref",
        metadata={"test": "metadata"},
        source="upload://test",
    )

    expected = {
        "uuid": str(upload.uuid),
        "filename": upload.filename,
        "track": serializers.TrackSerializer(upload.track).data,
        "duration": upload.duration,
        "mimetype": upload.mimetype,
        "bitrate": upload.bitrate,
        "size": upload.size,
        "library": serializers.LibraryForOwnerSerializer(upload.library).data,
        "creation_date": to_api_date(upload.creation_date),
        "metadata": {"test": "metadata"},
        "import_metadata": {"import": "metadata"},
        "import_date": None,
        "import_status": "success",
        "import_details": {"hello": "world"},
        "source": "upload://test",
        "import_reference": "ref",
    }
    serializer = serializers.UploadForOwnerSerializer(upload)
    assert serializer.data == expected


def test_album_serializer(factories, to_api_date):
    actor = factories["federation.Actor"]()
    track1 = factories["music.Track"](
        position=2, album__attributed_to=actor, album__with_cover=True
    )
    factories["music.Track"](position=1, album=track1.album)
    album = track1.album
    expected = {
        "id": album.id,
        "fid": album.fid,
        "mbid": str(album.mbid),
        "title": album.title,
        "artist": serializers.serialize_artist_simple(album.artist),
        "creation_date": to_api_date(album.creation_date),
        "is_playable": False,
        "cover": common_serializers.AttachmentSerializer(album.attachment_cover).data,
        "release_date": to_api_date(album.release_date),
        "tracks_count": 2,
        "is_local": album.is_local,
        "tags": [],
        "attributed_to": federation_serializers.APIActorSerializer(actor).data,
    }
    serializer = serializers.AlbumSerializer(
        album.__class__.objects.with_tracks_count().get(pk=album.pk)
    )

    assert serializer.data == expected


def test_album_serializer_empty_cover(factories, to_api_date):
    # XXX: BACKWARD COMPATIBILITY
    album = factories["music.Album"](attachment_cover=None)

    serializer = serializers.AlbumSerializer(album)

    assert serializer.data["cover"] == {}


def test_track_serializer(factories, to_api_date):
    actor = factories["federation.Actor"]()
    upload = factories["music.Upload"](
        track__license="cc-by-4.0",
        track__copyright="test",
        track__disc_number=2,
        track__attributed_to=actor,
        track__with_cover=True,
    )
    track = upload.track
    setattr(track, "playable_uploads", [upload])
    expected = {
        "id": track.id,
        "fid": track.fid,
        "artist": serializers.serialize_artist_simple(track.artist),
        "album": serializers.TrackAlbumSerializer(track.album).data,
        "mbid": str(track.mbid),
        "title": track.title,
        "position": track.position,
        "disc_number": track.disc_number,
        "uploads": [serializers.serialize_upload(upload)],
        "creation_date": to_api_date(track.creation_date),
        "listen_url": track.listen_url,
        "license": upload.track.license.code,
        "copyright": upload.track.copyright,
        "is_local": upload.track.is_local,
        "tags": [],
        "attributed_to": federation_serializers.APIActorSerializer(actor).data,
        "cover": common_serializers.AttachmentSerializer(track.attachment_cover).data,
    }
    serializer = serializers.TrackSerializer(track)
    assert serializer.data == expected


def test_user_cannot_bind_file_to_a_not_owned_library(factories):
    user = factories["users.User"]()
    library = factories["music.Library"]()

    s = serializers.UploadForOwnerSerializer(
        data={"library": library.uuid, "source": "upload://test"},
        context={"user": user},
    )
    assert s.is_valid() is False
    assert "library" in s.errors


def test_user_can_create_file_in_own_library(factories, uploaded_audio_file):
    user = factories["users.User"]()
    library = factories["music.Library"](actor__user=user)
    s = serializers.UploadForOwnerSerializer(
        data={
            "library": library.uuid,
            "source": "upload://test",
            "audio_file": uploaded_audio_file,
        },
        context={"user": user},
    )
    assert s.is_valid(raise_exception=True) is True
    upload = s.save()

    assert upload.library == library


def test_create_file_checks_for_user_quota(
    factories, preferences, uploaded_audio_file, mocker
):
    mocker.patch(
        "funkwhale_api.users.models.User.get_quota_status",
        return_value={"remaining": 0},
    )
    user = factories["users.User"]()
    library = factories["music.Library"](actor__user=user)
    s = serializers.UploadForOwnerSerializer(
        data={
            "library": library.uuid,
            "source": "upload://test",
            "audio_file": uploaded_audio_file,
        },
        context={"user": user},
    )
    assert s.is_valid() is False
    assert s.errors["non_field_errors"] == ["upload_quota_reached"]


def test_manage_upload_action_delete(factories, queryset_equal_list, mocker):
    dispatch = mocker.patch("funkwhale_api.federation.routes.outbox.dispatch")
    library1 = factories["music.Library"]()
    library2 = factories["music.Library"]()
    library1_uploads = factories["music.Upload"].create_batch(size=3, library=library1)
    library2_uploads = factories["music.Upload"].create_batch(size=3, library=library2)
    s = serializers.UploadActionSerializer(queryset=None)

    s.handle_delete(library1_uploads[0].__class__.objects.all())

    assert library1_uploads[0].__class__.objects.count() == 0
    dispatch.assert_any_call(
        {"type": "Delete", "object": {"type": "Audio"}},
        context={"uploads": library1_uploads},
    )
    dispatch.assert_any_call(
        {"type": "Delete", "object": {"type": "Audio"}},
        context={"uploads": library2_uploads},
    )


def test_manage_upload_action_relaunch_import(factories, mocker):
    m = mocker.patch("funkwhale_api.common.utils.on_commit")

    # this one is finished and should stay as is
    finished = factories["music.Upload"](import_status="finished")
    draft = factories["music.Upload"](import_status="draft")

    to_relaunch = [
        factories["music.Upload"](import_status="pending"),
        factories["music.Upload"](import_status="skipped"),
        factories["music.Upload"](import_status="errored"),
    ]
    s = serializers.UploadActionSerializer(queryset=None)

    s.handle_relaunch_import(models.Upload.objects.all())

    for obj in to_relaunch:
        obj.refresh_from_db()
        assert obj.import_status == "pending"
        m.assert_any_call(tasks.process_upload.delay, upload_id=obj.pk)

    finished.refresh_from_db()
    assert finished.import_status == "finished"
    draft.refresh_from_db()
    assert draft.import_status == "draft"
    assert m.call_count == 3


def test_manage_upload_action_publish(factories, mocker):
    m = mocker.patch("funkwhale_api.common.utils.on_commit")

    draft = factories["music.Upload"](import_status="draft")
    s = serializers.UploadActionSerializer(queryset=None)

    s.handle_publish(models.Upload.objects.all())

    draft.refresh_from_db()
    assert draft.import_status == "pending"
    m.assert_any_call(tasks.process_upload.delay, upload_id=draft.pk)


def test_serialize_upload(factories):
    upload = factories["music.Upload"]()

    expected = {
        "listen_url": upload.listen_url,
        "uuid": str(upload.uuid),
        "size": upload.size,
        "bitrate": upload.bitrate,
        "mimetype": upload.mimetype,
        "extension": upload.extension,
        "duration": upload.duration,
    }

    data = serializers.serialize_upload(upload)
    assert data == expected


@pytest.mark.parametrize(
    "field,before,after",
    [
        ("privacy_level", "me", "everyone"),
        ("name", "Before", "After"),
        ("description", "Before", "After"),
    ],
)
def test_update_library_privacy_level_broadcasts_to_followers(
    factories, field, before, after, mocker
):
    dispatch = mocker.patch("funkwhale_api.federation.routes.outbox.dispatch")
    library = factories["music.Library"](**{field: before})

    serializer = serializers.LibraryForOwnerSerializer(
        library, data={field: after}, partial=True
    )
    assert serializer.is_valid(raise_exception=True)
    serializer.save()

    dispatch.assert_called_once_with(
        {"type": "Update", "object": {"type": "Library"}}, context={"library": library}
    )


def test_upload_with_channel(factories, uploaded_audio_file):
    channel = factories["audio.Channel"](attributed_to__local=True)
    user = channel.attributed_to.user
    data = {
        "channel": channel.uuid,
        "audio_file": uploaded_audio_file,
        "import_status": "draft",
    }
    serializer = serializers.UploadForOwnerSerializer(
        data=data, context={"user": user},
    )
    assert serializer.is_valid(raise_exception=True) is True
    upload = serializer.save()

    assert upload.library == channel.library


def test_upload_with_not_owned_channel_fails(factories, uploaded_audio_file):
    channel = factories["audio.Channel"]()
    user = factories["users.User"]()
    data = {
        "channel": channel.uuid,
        "audio_file": uploaded_audio_file,
    }
    serializer = serializers.UploadForOwnerSerializer(
        data=data, context={"user": user},
    )
    assert serializer.is_valid() is False
    assert "channel" in serializer.errors


def test_upload_with_not_owned_library_fails(factories, uploaded_audio_file):
    library = factories["music.Library"]()
    user = factories["users.User"]()
    data = {
        "library": library.uuid,
        "audio_file": uploaded_audio_file,
    }
    serializer = serializers.UploadForOwnerSerializer(
        data=data, context={"user": user},
    )
    assert serializer.is_valid() is False
    assert "library" in serializer.errors


def test_upload_requires_library_or_channel(factories, uploaded_audio_file):
    user = factories["users.User"]()
    data = {
        "audio_file": uploaded_audio_file,
    }
    serializer = serializers.UploadForOwnerSerializer(
        data=data, context={"user": user},
    )

    with pytest.raises(
        serializers.serializers.ValidationError,
        match=r"You need to specify a channel or a library",
    ):
        serializer.is_valid(raise_exception=True)


def test_upload_requires_library_or_channel_but_not_both(
    factories, uploaded_audio_file
):
    channel = factories["audio.Channel"](attributed_to__local=True)
    library = channel.library
    user = channel.attributed_to.user
    data = {
        "audio_file": uploaded_audio_file,
        "library": library.uuid,
        "channel": channel.uuid,
    }
    serializer = serializers.UploadForOwnerSerializer(
        data=data, context={"user": user},
    )
    with pytest.raises(
        serializers.serializers.ValidationError,
        match=r"You may specify a channel or a library, not both",
    ):
        serializer.is_valid(raise_exception=True)


def test_upload_import_metadata_serializer_simple():
    serializer = serializers.ImportMetadataSerializer(data={"title": "hello"})

    assert serializer.is_valid(raise_exception=True) is True
    assert serializer.validated_data == {"title": "hello"}


def test_upload_import_metadata_serializer_full():
    licenses.load(licenses.LICENSES)
    data = {
        "title": "hello",
        "mbid": "3220fd02-5237-4952-8394-b7e64b0204a6",
        "tags": ["politics", "gender"],
        "license": "cc-by-sa-4.0",
        "copyright": "My work",
        "position": 42,
    }
    expected = data.copy()
    expected["license"] = models.License.objects.get(code=data["license"])
    expected["mbid"] = uuid.UUID(data["mbid"])
    serializer = serializers.ImportMetadataSerializer(data=data)

    assert serializer.is_valid(raise_exception=True) is True
    assert serializer.validated_data == expected


def test_upload_import_metadata_serializer_channel_checks_owned_album(factories):
    channel = factories["audio.Channel"]()
    album = factories["music.Album"]()
    data = {"title": "hello", "album": album.pk}
    serializer = serializers.ImportMetadataSerializer(
        data=data, context={"channel": channel}
    )

    with pytest.raises(serializers.serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_upload_with_channel_keeps_import_metadata(factories, uploaded_audio_file):
    channel = factories["audio.Channel"](attributed_to__local=True)
    user = channel.attributed_to.user
    data = {
        "channel": channel.uuid,
        "audio_file": uploaded_audio_file,
        "import_metadata": {"title": "hello"},
    }
    serializer = serializers.UploadForOwnerSerializer(
        data=data, context={"user": user},
    )
    assert serializer.is_valid(raise_exception=True) is True
    upload = serializer.save()

    assert upload.import_metadata == data["import_metadata"]


def test_upload_with_channel_validates_import_metadata(factories, uploaded_audio_file):
    channel = factories["audio.Channel"](attributed_to__local=True)
    user = channel.attributed_to.user
    data = {
        "channel": channel.uuid,
        "audio_file": uploaded_audio_file,
        "import_metadata": {"title": None},
    }
    serializer = serializers.UploadForOwnerSerializer(
        data=data, context={"user": user},
    )
    with pytest.raises(serializers.serializers.ValidationError):
        assert serializer.is_valid(raise_exception=True)


@pytest.mark.parametrize(
    "factory_name, serializer_class",
    [
        ("music.Artist", serializers.ArtistWithAlbumsSerializer),
        ("music.Album", serializers.AlbumSerializer),
        ("music.Track", serializers.TrackSerializer),
    ],
)
def test_detail_serializers_with_description_description(
    factory_name, serializer_class, factories
):
    content = factories["common.Content"]()
    obj = factories[factory_name](description=content)
    expected = common_serializers.ContentSerializer(content).data
    serializer = serializer_class(obj, context={"description": True})
    assert serializer.data["description"] == expected


def test_sort_uploads_for_listen(factories):
    local_upload = factories["music.Upload"](library__local=True)
    new_local_upload = factories["music.Upload"](library__local=True)
    remote_upload = factories["music.Upload"](audio_file__from_path=None)
    remote_upload_with_local_version = factories["music.Upload"]()

    unsorted = [
        remote_upload_with_local_version,
        new_local_upload,
        remote_upload,
        local_upload,
    ]
    expected = [
        local_upload,
        new_local_upload,
        remote_upload,
        remote_upload_with_local_version,
    ]
    assert serializers.sort_uploads_for_listen(unsorted) == expected

import os
import pytest

from funkwhale_api.common import utils as common_utils
from funkwhale_api.music.management.commands import check_inplace_files
from funkwhale_api.music.management.commands import fix_uploads
from funkwhale_api.music.management.commands import prune_library

DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def test_fix_uploads_bitrate_length(factories, mocker):
    upload1 = factories["music.Upload"](bitrate=1, duration=2)
    upload2 = factories["music.Upload"](bitrate=None, duration=None)
    c = fix_uploads.Command()

    mocker.patch(
        "funkwhale_api.music.utils.get_audio_file_data",
        return_value={"bitrate": 42, "length": 43},
    )

    c.fix_file_data(dry_run=False, batch_size=100)

    upload1.refresh_from_db()
    upload2.refresh_from_db()

    # not updated
    assert upload1.bitrate == 1
    assert upload1.duration == 2

    # updated
    assert upload2.bitrate == 42
    assert upload2.duration == 43


def test_fix_uploads_size(factories, mocker):
    upload1 = factories["music.Upload"]()
    upload2 = factories["music.Upload"]()
    upload1.__class__.objects.filter(pk=upload1.pk).update(size=1)
    upload2.__class__.objects.filter(pk=upload2.pk).update(size=None)
    c = fix_uploads.Command()

    mocker.patch("funkwhale_api.music.models.Upload.get_file_size", return_value=2)

    c.fix_file_size(dry_run=False, batch_size=100)

    upload1.refresh_from_db()
    upload2.refresh_from_db()

    # not updated
    assert upload1.size == 1

    # updated
    assert upload2.size == 2


def test_fix_uploads_mimetype(factories, mocker):
    mp3_path = os.path.join(DATA_DIR, "test.mp3")
    ogg_path = os.path.join(DATA_DIR, "test.ogg")
    upload1 = factories["music.Upload"](
        audio_file__from_path=mp3_path,
        source="file://{}".format(mp3_path),
        mimetype="application/x-empty",
    )

    # this one already has a mimetype set, to it should not be updated
    upload2 = factories["music.Upload"](
        audio_file__from_path=ogg_path,
        source="file://{}".format(ogg_path),
        mimetype="audio/something",
    )
    c = fix_uploads.Command()
    c.fix_mimetypes(dry_run=False, batch_size=100)

    upload1.refresh_from_db()
    upload2.refresh_from_db()

    assert upload1.mimetype == "audio/mpeg"
    assert upload2.mimetype == "audio/something"


def test_fix_uploads_checksum(factories, mocker):
    upload1 = factories["music.Upload"]()
    upload2 = factories["music.Upload"]()
    upload1.__class__.objects.filter(pk=upload1.pk).update(checksum="test")
    upload2.__class__.objects.filter(pk=upload2.pk).update(checksum=None)
    c = fix_uploads.Command()

    c.fix_file_checksum(dry_run=False, batch_size=100)

    upload1.refresh_from_db()
    upload2.refresh_from_db()

    # not updated
    assert upload1.checksum == "test"

    # updated
    assert upload2.checksum == common_utils.get_file_hash(upload2.audio_file)


def test_prune_library_dry_run(factories):
    prunable = factories["music.Track"]()
    not_prunable = factories["music.Track"]()
    c = prune_library.Command()
    options = {
        "prune_artists": True,
        "prune_albums": True,
        "prune_tracks": True,
        "exclude_favorites": False,
        "exclude_listenings": False,
        "exclude_playlists": False,
        "dry_run": True,
    }
    c.handle(**options)

    for t in [prunable, not_prunable]:
        # nothing pruned, because dry run
        t.refresh_from_db()


def test_prune_library(factories, mocker):
    prunable_track = factories["music.Track"]()
    not_prunable_track = factories["music.Track"]()
    prunable_tracks = prunable_track.__class__.objects.filter(pk=prunable_track.pk)
    get_prunable_tracks = mocker.patch(
        "funkwhale_api.music.tasks.get_prunable_tracks", return_value=prunable_tracks
    )

    prunable_album = factories["music.Album"]()
    not_prunable_album = factories["music.Album"]()
    prunable_albums = prunable_album.__class__.objects.filter(pk=prunable_album.pk)
    get_prunable_albums = mocker.patch(
        "funkwhale_api.music.tasks.get_prunable_albums", return_value=prunable_albums
    )

    prunable_artist = factories["music.Artist"]()
    not_prunable_artist = factories["music.Artist"]()
    prunable_artists = prunable_artist.__class__.objects.filter(pk=prunable_artist.pk)
    get_prunable_artists = mocker.patch(
        "funkwhale_api.music.tasks.get_prunable_artists", return_value=prunable_artists
    )

    c = prune_library.Command()
    options = {
        "exclude_favorites": mocker.Mock(),
        "exclude_listenings": mocker.Mock(),
        "exclude_playlists": mocker.Mock(),
        "prune_artists": True,
        "prune_albums": True,
        "prune_tracks": True,
        "dry_run": False,
    }
    c.handle(**options)

    get_prunable_tracks.assert_called_once_with(
        exclude_favorites=options["exclude_favorites"],
        exclude_listenings=options["exclude_listenings"],
        exclude_playlists=options["exclude_playlists"],
    )
    get_prunable_albums.assert_called_once()
    get_prunable_artists.assert_called_once()

    with pytest.raises(prunable_track.DoesNotExist):
        prunable_track.refresh_from_db()

    with pytest.raises(prunable_album.DoesNotExist):
        prunable_album.refresh_from_db()

    with pytest.raises(prunable_artist.DoesNotExist):
        prunable_artist.refresh_from_db()

    for o in [not_prunable_track, not_prunable_album, not_prunable_artist]:
        o.refresh_from_db()


def test_check_inplace_files_dry_run(factories, tmpfile):
    prunable = factories["music.Upload"](source="file:///notfound", audio_file=None)
    not_prunable = factories["music.Upload"](
        source="file://{}".format(tmpfile.name), audio_file=None
    )
    c = check_inplace_files.Command()
    c.handle(dry_run=True)

    for u in [prunable, not_prunable]:
        # nothing pruned, because dry run
        u.refresh_from_db()


def test_check_inplace_files_no_dry_run(factories, tmpfile):
    prunable = factories["music.Upload"](source="file:///notfound", audio_file=None)
    not_prunable = [
        factories["music.Upload"](
            source="file://{}".format(tmpfile.name), audio_file=None
        ),
        factories["music.Upload"](source="upload://"),
        factories["music.Upload"](source="https://"),
    ]
    c = check_inplace_files.Command()
    c.handle(dry_run=False)

    with pytest.raises(prunable.DoesNotExist):
        prunable.refresh_from_db()

    for u in not_prunable:
        u.refresh_from_db()

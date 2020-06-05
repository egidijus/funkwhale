import os

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from funkwhale_api.common import utils as common_utils
from funkwhale_api.music.management.commands import import_files

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "files")


def test_management_command_requires_a_valid_library_id(factories):
    path = os.path.join(DATA_DIR, "dummy_file.ogg")

    with pytest.raises(CommandError, match=r".*Invalid library id.*"):
        call_command("import_files", "wrong_id", path, interactive=False)


def test_in_place_import_only_from_music_dir(factories, settings):
    library = factories["music.Library"](actor__local=True)
    settings.MUSIC_DIRECTORY_PATH = "/nope"
    path = os.path.join(DATA_DIR, "dummy_file.ogg")
    with pytest.raises(
        CommandError, match=r".*Importing in-place only works if importing.*"
    ):
        call_command(
            "import_files", str(library.uuid), path, in_place=True, interactive=False
        )


def test_import_with_multiple_argument(factories, mocker):
    library = factories["music.Library"](actor__local=True)
    path1 = os.path.join(DATA_DIR, "dummy_file.ogg")
    path2 = os.path.join(DATA_DIR, "utf8-éà◌.ogg")
    mocked_filter = mocker.patch(
        "funkwhale_api.music.management.commands.import_files.Command.filter_matching",
        return_value=({"new": [], "skipped": []}),
    )
    call_command("import_files", str(library.uuid), path1, path2, interactive=False)
    mocked_filter.assert_called_once_with([path1, path2], library)


@pytest.mark.parametrize(
    "path",
    [os.path.join(DATA_DIR, "dummy_file.ogg"), os.path.join(DATA_DIR, "utf8-éà◌.ogg")],
)
def test_import_files_stores_proper_data(factories, mocker, now, path):
    mocked_process = mocker.patch("funkwhale_api.music.tasks.process_upload")
    library = factories["music.Library"](actor__local=True)
    call_command(
        "import_files", str(library.uuid), path, async_=False, interactive=False
    )
    upload = library.uploads.last()
    assert upload.import_reference == "cli-{}".format(now.isoformat())
    assert upload.import_status == "pending"
    assert upload.source == "file://{}".format(path)
    assert upload.import_metadata == {
        "funkwhale": {
            "config": {"replace": False, "dispatch_outbox": False, "broadcast": False}
        }
    }

    mocked_process.assert_called_once_with(upload_id=upload.pk)


def test_import_with_outbox_flag(factories, mocker):
    library = factories["music.Library"](actor__local=True)
    path = os.path.join(DATA_DIR, "dummy_file.ogg")
    mocked_process = mocker.patch("funkwhale_api.music.tasks.process_upload")
    call_command(
        "import_files", str(library.uuid), path, outbox=True, interactive=False
    )
    upload = library.uploads.last()

    assert upload.import_metadata["funkwhale"]["config"]["dispatch_outbox"] is True

    mocked_process.assert_called_once_with(upload_id=upload.pk)


def test_import_with_broadcast_flag(factories, mocker):
    library = factories["music.Library"](actor__local=True)
    path = os.path.join(DATA_DIR, "dummy_file.ogg")
    mocked_process = mocker.patch("funkwhale_api.music.tasks.process_upload")
    call_command(
        "import_files", str(library.uuid), path, broadcast=True, interactive=False
    )
    upload = library.uploads.last()

    assert upload.import_metadata["funkwhale"]["config"]["broadcast"] is True

    mocked_process.assert_called_once_with(upload_id=upload.pk)


def test_import_with_replace_flag(factories, mocker):
    library = factories["music.Library"](actor__local=True)
    path = os.path.join(DATA_DIR, "dummy_file.ogg")
    mocked_process = mocker.patch("funkwhale_api.music.tasks.process_upload")
    call_command(
        "import_files", str(library.uuid), path, replace=True, interactive=False
    )
    upload = library.uploads.last()

    assert upload.import_metadata["funkwhale"]["config"]["replace"] is True

    mocked_process.assert_called_once_with(upload_id=upload.pk)


def test_import_with_custom_reference(factories, mocker):
    library = factories["music.Library"](actor__local=True)
    path = os.path.join(DATA_DIR, "dummy_file.ogg")
    mocked_process = mocker.patch("funkwhale_api.music.tasks.process_upload")
    call_command(
        "import_files",
        str(library.uuid),
        path,
        reference="test",
        replace=True,
        interactive=False,
    )
    upload = library.uploads.last()

    assert upload.import_reference == "test"

    mocked_process.assert_called_once_with(upload_id=upload.pk)


def test_import_files_skip_if_path_already_imported(factories, mocker):
    library = factories["music.Library"](actor__local=True)
    path = os.path.join(DATA_DIR, "dummy_file.ogg")

    # existing one with same source
    factories["music.Upload"](
        library=library, import_status="finished", source="file://{}".format(path)
    )

    call_command(
        "import_files", str(library.uuid), path, async_=False, interactive=False
    )
    assert library.uploads.count() == 1


def test_import_files_in_place(factories, mocker, settings):
    settings.MUSIC_DIRECTORY_PATH = DATA_DIR
    mocked_process = mocker.patch("funkwhale_api.music.tasks.process_upload")
    library = factories["music.Library"](actor__local=True)
    path = os.path.join(DATA_DIR, "utf8-éà◌.ogg")
    call_command(
        "import_files",
        str(library.uuid),
        path,
        async_=False,
        in_place=True,
        interactive=False,
    )
    upload = library.uploads.last()
    assert bool(upload.audio_file) is False
    mocked_process.assert_called_once_with(upload_id=upload.pk)


def test_storage_rename_utf_8_files(factories):
    upload = factories["music.Upload"](audio_file__filename="été.ogg")
    assert upload.audio_file.name.endswith("ete.ogg")


@pytest.mark.parametrize("name", ["modified", "moved", "created", "deleted"])
def test_handle_event(name, mocker):
    handler = mocker.patch.object(import_files, "handle_{}".format(name))

    event = {"type": name}
    stdout = mocker.Mock()
    kwargs = {"hello": "world"}
    import_files.handle_event(event, stdout, **kwargs)

    handler.assert_called_once_with(event=event, stdout=stdout, **kwargs)


def test_handle_created(mocker):
    handle_modified = mocker.patch.object(import_files, "handle_modified")

    event = mocker.Mock()
    stdout = mocker.Mock()
    kwargs = {"hello": "world"}
    import_files.handle_created(event, stdout, **kwargs)

    handle_modified.assert_called_once_with(event, stdout, **kwargs)


def test_handle_deleted(factories, mocker):
    stdout = mocker.Mock()
    event = {
        "path": "/path.mp3",
    }
    library = factories["music.Library"]()
    deleted = factories["music.Upload"](
        library=library,
        source="file://{}".format(event["path"]),
        import_status="finished",
        audio_file=None,
    )
    kept = [
        factories["music.Upload"](
            library=library,
            source="file://{}".format(event["path"]),
            import_status="finished",
        ),
        factories["music.Upload"](
            source="file://{}".format(event["path"]),
            import_status="finished",
            audio_file=None,
        ),
    ]

    import_files.handle_deleted(
        event=event, stdout=stdout, library=library, in_place=True
    )

    with pytest.raises(deleted.DoesNotExist):
        deleted.refresh_from_db()

    for upload in kept:
        upload.refresh_from_db()


def test_handle_moved(factories, mocker):
    stdout = mocker.Mock()
    event = {
        "src_path": "/path.mp3",
        "dest_path": "/new_path.mp3",
    }
    library = factories["music.Library"]()
    updated = factories["music.Upload"](
        library=library,
        source="file://{}".format(event["src_path"]),
        import_status="finished",
        audio_file=None,
    )
    untouched = [
        factories["music.Upload"](
            library=library,
            source="file://{}".format(event["src_path"]),
            import_status="finished",
        ),
        factories["music.Upload"](
            source="file://{}".format(event["src_path"]),
            import_status="finished",
            audio_file=None,
        ),
    ]

    import_files.handle_moved(
        event=event, stdout=stdout, library=library, in_place=True
    )

    updated.refresh_from_db()
    assert updated.source == "file://{}".format(event["dest_path"])
    for upload in untouched:
        source = upload.source
        upload.refresh_from_db()
        assert source == upload.source


def test_handle_modified_creates_upload(tmpfile, factories, mocker):
    stdout = mocker.Mock()
    event = {
        "path": tmpfile.name,
    }
    process_upload = mocker.patch("funkwhale_api.music.tasks.process_upload")
    library = factories["music.Library"]()
    import_files.handle_modified(
        event=event,
        stdout=stdout,
        library=library,
        in_place=True,
        reference="hello",
        replace=False,
        dispatch_outbox=False,
        broadcast=False,
    )
    upload = library.uploads.latest("id")
    assert upload.source == "file://{}".format(event["path"])

    process_upload.assert_called_once_with(upload_id=upload.pk)


def test_handle_modified_skips_existing_checksum(tmpfile, factories, mocker):
    stdout = mocker.Mock()
    event = {
        "path": tmpfile.name,
    }
    tmpfile.write(b"hello")

    library = factories["music.Library"]()
    factories["music.Upload"](
        checksum=common_utils.get_file_hash(tmpfile),
        library=library,
        import_status="finished",
    )
    import_files.handle_modified(
        event=event, stdout=stdout, library=library, in_place=True,
    )
    assert library.uploads.count() == 1


def test_handle_modified_update_existing_path_if_found(tmpfile, factories, mocker):
    stdout = mocker.Mock()
    event = {
        "path": tmpfile.name,
    }
    update_track_metadata = mocker.patch(
        "funkwhale_api.music.tasks.update_track_metadata"
    )
    get_metadata = mocker.patch("funkwhale_api.music.models.Upload.get_metadata")
    library = factories["music.Library"]()
    track = factories["music.Track"](attributed_to=library.actor)
    upload = factories["music.Upload"](
        source="file://{}".format(event["path"]),
        track=track,
        checksum="old",
        library=library,
        import_status="finished",
        audio_file=None,
    )
    import_files.handle_modified(
        event=event, stdout=stdout, library=library, in_place=True,
    )
    update_track_metadata.assert_called_once_with(
        get_metadata.return_value, upload.track,
    )


def test_handle_modified_update_existing_path_if_found_and_attributed_to(
    tmpfile, factories, mocker
):
    stdout = mocker.Mock()
    event = {
        "path": tmpfile.name,
    }
    update_track_metadata = mocker.patch(
        "funkwhale_api.music.tasks.update_track_metadata"
    )
    library = factories["music.Library"]()
    factories["music.Upload"](
        source="file://{}".format(event["path"]),
        checksum="old",
        library=library,
        track__attributed_to=factories["federation.Actor"](),
        import_status="finished",
        audio_file=None,
    )
    import_files.handle_modified(
        event=event, stdout=stdout, library=library, in_place=True,
    )
    update_track_metadata.assert_not_called()


def test_import_files(factories, capsys):
    # smoke test to ensure the command run properly
    library = factories["music.Library"](actor__local=True)
    call_command(
        "import_files", str(library.uuid), DATA_DIR, interactive=False, recursive=True
    )
    captured = capsys.readouterr()

    imported = library.uploads.filter(import_status="finished").count()
    assert imported > 0
    assert "Successfully imported {} new tracks".format(imported) in captured.out
    assert "For details, please refer to import reference" in captured.out

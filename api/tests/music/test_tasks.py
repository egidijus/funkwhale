import os
import pytest

from funkwhale_api.providers.acoustid import get_acoustid_client
from funkwhale_api.music import tasks

from . import data as api_data

DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def test_set_acoustid_on_track_file(factories, mocker):
    track_file = factories['music.TrackFile'](acoustid_track_id=None)
    id = 'e475bf79-c1ce-4441-bed7-1e33f226c0a2'
    payload = {
        'results': [
            {'id': id,
             'recordings': [
                {'artists': [
                    {'id': '9c6bddde-6228-4d9f-ad0d-03f6fcb19e13',
                     'name': 'Binärpilot'}],
                 'duration': 268,
                 'id': 'f269d497-1cc0-4ae4-a0c4-157ec7d73fcb',
                 'title': 'Bend'}],
            'score': 0.860825}],
        'status': 'ok'
    }
    m = mocker.patch('acoustid.match', return_value=payload)
    r = tasks.set_acoustid_on_track_file(track_file_id=track_file.pk)
    track_file.refresh_from_db()

    assert str(track_file.acoustid_track_id) == id
    assert r == id
    m.assert_called_once_with('', track_file.audio_file.path, parse=False)


def test_set_acoustid_on_track_file_required_high_score(factories, mocker):
    track_file = factories['music.TrackFile'](acoustid_track_id=None)
    id = 'e475bf79-c1ce-4441-bed7-1e33f226c0a2'
    payload = {
        'results': [{'score': 0.79}],
        'status': 'ok'
    }
    m = mocker.patch('acoustid.match', return_value=payload)
    r = tasks.set_acoustid_on_track_file(track_file_id=track_file.pk)
    track_file.refresh_from_db()

    assert track_file.acoustid_track_id is None


def test_import_job_can_run_with_file_and_acoustid(factories, mocker):
    path = os.path.join(DATA_DIR, 'test.ogg')
    mbid = '9968a9d6-8d92-4051-8f76-674e157b6eed'
    acoustid_payload = {
        'results': [
            {'id': 'e475bf79-c1ce-4441-bed7-1e33f226c0a2',
             'recordings': [
                {
                 'duration': 268,
                 'id': mbid}],
            'score': 0.860825}],
        'status': 'ok'
    }
    mocker.patch(
        'funkwhale_api.musicbrainz.api.artists.get',
        return_value=api_data.artists['get']['adhesive_wombat'])
    mocker.patch(
        'funkwhale_api.musicbrainz.api.releases.get',
        return_value=api_data.albums['get']['marsupial'])
    mocker.patch(
        'funkwhale_api.musicbrainz.api.recordings.search',
        return_value=api_data.tracks['search']['8bitadventures'])
    mocker.patch('acoustid.match', return_value=acoustid_payload)

    job = factories['music.FileImportJob'](audio_file__path=path)
    f = job.audio_file
    tasks.import_job_run(import_job_id=job.pk)
    job.refresh_from_db()

    track_file = job.track_file

    with open(path, 'rb') as f:
        assert track_file.audio_file.read() == f.read()
    assert track_file.duration == 268
    # audio file is deleted from import job once persisted to audio file
    assert not job.audio_file
    assert job.status == 'finished'
    assert job.source == 'file://'


def test_import_job_can_be_skipped(factories, mocker):
    path = os.path.join(DATA_DIR, 'test.ogg')
    mbid = '9968a9d6-8d92-4051-8f76-674e157b6eed'
    track_file = factories['music.TrackFile'](track__mbid=mbid)
    acoustid_payload = {
        'results': [
            {'id': 'e475bf79-c1ce-4441-bed7-1e33f226c0a2',
             'recordings': [
                {
                 'duration': 268,
                 'id': mbid}],
            'score': 0.860825}],
        'status': 'ok'
    }
    mocker.patch(
        'funkwhale_api.musicbrainz.api.artists.get',
        return_value=api_data.artists['get']['adhesive_wombat'])
    mocker.patch(
        'funkwhale_api.musicbrainz.api.releases.get',
        return_value=api_data.albums['get']['marsupial'])
    mocker.patch(
        'funkwhale_api.musicbrainz.api.recordings.search',
        return_value=api_data.tracks['search']['8bitadventures'])
    mocker.patch('acoustid.match', return_value=acoustid_payload)

    job = factories['music.FileImportJob'](audio_file__path=path)
    f = job.audio_file
    tasks.import_job_run(import_job_id=job.pk)
    job.refresh_from_db()

    assert job.track_file is None
    # audio file is deleted from import job once persisted to audio file
    assert not job.audio_file
    assert job.status == 'skipped'


def test_import_job_can_be_errored(factories, mocker):
    path = os.path.join(DATA_DIR, 'test.ogg')
    mbid = '9968a9d6-8d92-4051-8f76-674e157b6eed'
    track_file = factories['music.TrackFile'](track__mbid=mbid)
    acoustid_payload = {
        'results': [
            {'id': 'e475bf79-c1ce-4441-bed7-1e33f226c0a2',
             'recordings': [
                {
                 'duration': 268,
                 'id': mbid}],
            'score': 0.860825}],
        'status': 'ok'
    }
    class MyException(Exception):
        pass
    mocker.patch('acoustid.match', side_effect=MyException())

    job = factories['music.FileImportJob'](
        audio_file__path=path, track_file=None)

    with pytest.raises(MyException):
        tasks.import_job_run(import_job_id=job.pk)
    job.refresh_from_db()

    assert job.track_file is None
    assert job.status == 'errored'
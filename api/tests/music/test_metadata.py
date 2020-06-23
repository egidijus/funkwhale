import datetime
import os
import uuid
import pytest

import mutagen.oggtheora
import mutagen.oggvorbis

from funkwhale_api.music import metadata

DATA_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", "Peer Gynt Suite no. 1, op. 46: I. Morning"),
        ("artist", "Edvard Grieg"),
        ("album_artist", "Edvard Grieg; Musopen Symphony Orchestra"),
        ("artists", "Edvard Grieg; Musopen Symphony Orchestra"),
        ("album", "Peer Gynt Suite no. 1, op. 46"),
        ("date", "2012-08-15"),
        ("position", "1"),
        ("disc_number", "1"),
        ("musicbrainz_albumid", "a766da8b-8336-47aa-a3ee-371cc41ccc75"),
        ("mbid", "bd21ac48-46d8-4e78-925f-d9cc2a294656"),
        ("musicbrainz_artistid", "013c8e5b-d72a-4cd3-8dee-6c64d6125823"),
        (
            "musicbrainz_albumartistid",
            "013c8e5b-d72a-4cd3-8dee-6c64d6125823;5b4d7d2d-36df-4b38-95e3-a964234f520f",
        ),
        ("license", "Dummy license: http://creativecommons.org/licenses/by-sa/4.0/"),
        ("copyright", "Someone"),
        ("comment", "Hello there"),
    ],
)
def test_can_get_metadata_from_ogg_file(field, value):
    path = os.path.join(DATA_DIR, "test.ogg")
    data = metadata.Metadata(path)

    assert data.get(field) == value


def test_can_get_metadata_all():
    path = os.path.join(DATA_DIR, "test.ogg")
    data = metadata.Metadata(path)

    expected = {
        "title": "Peer Gynt Suite no. 1, op. 46: I. Morning",
        "artist": "Edvard Grieg",
        "album_artist": "Edvard Grieg; Musopen Symphony Orchestra",
        "artists": "Edvard Grieg; Musopen Symphony Orchestra",
        "album": "Peer Gynt Suite no. 1, op. 46",
        "date": "2012-08-15",
        "position": "1",
        "disc_number": "1",
        "musicbrainz_albumid": "a766da8b-8336-47aa-a3ee-371cc41ccc75",
        "mbid": "bd21ac48-46d8-4e78-925f-d9cc2a294656",
        "musicbrainz_artistid": "013c8e5b-d72a-4cd3-8dee-6c64d6125823",
        "musicbrainz_albumartistid": "013c8e5b-d72a-4cd3-8dee-6c64d6125823;5b4d7d2d-36df-4b38-95e3-a964234f520f",
        "license": "Dummy license: http://creativecommons.org/licenses/by-sa/4.0/",
        "copyright": "Someone",
        "genre": "Classical",
        "comment": "Hello there",
    }
    assert data.all() == expected


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", "Peer Gynt Suite no. 1, op. 46: I. Morning"),
        ("artist", "Edvard Grieg"),
        ("album_artist", "Edvard Grieg; Musopen Symphony Orchestra"),
        ("artists", "Edvard Grieg; Musopen Symphony Orchestra"),
        ("album", "Peer Gynt Suite no. 1, op. 46"),
        ("date", "2012-08-15"),
        ("position", "1"),
        ("disc_number", "1"),
        ("musicbrainz_albumid", "a766da8b-8336-47aa-a3ee-371cc41ccc75"),
        ("mbid", "bd21ac48-46d8-4e78-925f-d9cc2a294656"),
        ("musicbrainz_artistid", "013c8e5b-d72a-4cd3-8dee-6c64d6125823"),
        (
            "musicbrainz_albumartistid",
            "013c8e5b-d72a-4cd3-8dee-6c64d6125823;5b4d7d2d-36df-4b38-95e3-a964234f520f",
        ),
        ("license", "Dummy license: http://creativecommons.org/licenses/by-sa/4.0/"),
        ("copyright", "Someone"),
        ("comment", "Hello there"),
    ],
)
def test_can_get_metadata_from_opus_file(field, value):
    path = os.path.join(DATA_DIR, "test.opus")
    data = metadata.Metadata(path)

    assert data.get(field) == value


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", "Drei Kreuze (dass wir hier sind)"),
        ("artist", "Die Toten Hosen"),
        ("album_artist", "Die Toten Hosen"),
        ("album", "Ballast der Republik"),
        ("date", "2012-05-04"),
        ("position", "1/16"),
        ("disc_number", "1/2"),
        ("musicbrainz_albumid", "1f0441ad-e609-446d-b355-809c445773cf"),
        ("mbid", "124d0150-8627-46bc-bc14-789a3bc960c8"),
        ("musicbrainz_artistid", "c3bc80a6-1f4a-4e17-8cf0-6b1efe8302f1"),
        ("musicbrainz_albumartistid", "c3bc80a6-1f4a-4e17-8cf0-6b1efe8302f1"),
        ("comment", "Hello there"),
        # somehow, I cannot successfully create an ogg theora file
        # with the proper license field
        # ("license", "Dummy license: http://creativecommons.org/licenses/by-sa/4.0/"),
    ],
)
def test_can_get_metadata_from_ogg_theora_file(field, value):
    path = os.path.join(DATA_DIR, "test_theora.ogg")
    data = metadata.Metadata(path)

    assert data.get(field) == value


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", "Bend"),
        ("artist", "Binärpilot"),
        ("album_artist", "Binärpilot"),
        ("artists", "Binärpilot; Another artist"),
        ("album", "You Can't Stop Da Funk"),
        ("date", "2006-02-07"),
        ("position", "2/4"),
        ("disc_number", "1/1"),
        ("musicbrainz_albumid", "ce40cdb1-a562-4fd8-a269-9269f98d4124"),
        ("mbid", "f269d497-1cc0-4ae4-a0c4-157ec7d73fcb"),
        ("musicbrainz_artistid", "9c6bddde-6228-4d9f-ad0d-03f6fcb19e13"),
        ("musicbrainz_albumartistid", "9c6bddde-6228-4d9f-ad0d-03f6fcb19e13"),
        ("license", "https://creativecommons.org/licenses/by-nc-nd/2.5/"),
        ("copyright", "Someone"),
        ("comment", "Hello there"),
    ],
)
def test_can_get_metadata_from_id3_mp3_file(field, value):
    path = os.path.join(DATA_DIR, "test.mp3")
    data = metadata.Metadata(path)

    assert str(data.get(field)) == value


@pytest.mark.parametrize(
    "name",
    [
        "test.mp3",
        "with_other_picture.mp3",
        "sample.flac",
        "with_cover.ogg",
        "with_cover.opus",
        "test.m4a",
    ],
)
def test_can_get_pictures(name):
    path = os.path.join(DATA_DIR, name)
    data = metadata.Metadata(path)

    pictures = data.get("pictures")
    assert len(pictures) == 1
    cover_data = data.get_picture("cover_front", "other")
    assert cover_data["mimetype"].startswith("image/")
    assert len(cover_data["content"]) > 0
    assert type(cover_data["content"]) == bytes
    assert type(cover_data["description"]) == str


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", "999,999"),
        ("artist", "Nine Inch Nails"),
        ("album_artist", "Nine Inch Nails"),
        ("album", "The Slip"),
        ("date", "2008-05-05"),
        ("position", "1"),
        ("disc_number", "1"),
        ("musicbrainz_albumid", "12b57d46-a192-499e-a91f-7da66790a1c1"),
        ("mbid", "30f3f33e-8d0c-4e69-8539-cbd701d18f28"),
        ("musicbrainz_artistid", "b7ffd2af-418f-4be2-bdd1-22f8b48613da"),
        ("musicbrainz_albumartistid", "b7ffd2af-418f-4be2-bdd1-22f8b48613da"),
        ("license", "http://creativecommons.org/licenses/by-nc-sa/3.0/us/"),
        ("copyright", "2008 nin"),
        ("comment", "Hello there"),
    ],
)
def test_can_get_metadata_from_flac_file(field, value):
    path = os.path.join(DATA_DIR, "sample.flac")
    data = metadata.Metadata(path)

    assert data.get(field) == value


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", "Peer Gynt Suite no. 1, op. 46: I. Morning"),
        ("artist", "Edvard Grieg"),
        ("album_artist", "Edvard Grieg; Musopen Symphony Orchestra"),
        ("artists", "Edvard Grieg; Musopen Symphony Orchestra"),
        ("album", "Peer Gynt Suite no. 1, op. 46"),
        ("date", "2012-08-15"),
        ("position", 1),
        ("disc_number", 2),
        ("musicbrainz_albumid", "a766da8b-8336-47aa-a3ee-371cc41ccc75"),
        ("mbid", "bd21ac48-46d8-4e78-925f-d9cc2a294656"),
        ("musicbrainz_artistid", "013c8e5b-d72a-4cd3-8dee-6c64d6125823"),
        (
            "musicbrainz_albumartistid",
            "013c8e5b-d72a-4cd3-8dee-6c64d6125823;5b4d7d2d-36df-4b38-95e3-a964234f520f",
        ),
        ("license", "Dummy license: http://creativecommons.org/licenses/by-sa/4.0/"),
        ("copyright", "Someone"),
        ("genre", "Dubstep"),
        ("comment", "Hello there"),
    ],
)
def test_can_get_metadata_from_m4a_file(field, value):
    path = os.path.join(DATA_DIR, "test.m4a")
    data = metadata.Metadata(path)

    assert data.get(field) == value


def test_get_pictures_m4a_empty():
    pictures = metadata.get_mp4_tag({}, "pictures")
    assert metadata.clean_mp4_pictures(pictures) == []


def test_can_get_metadata_from_flac_file_not_crash_if_empty():
    path = os.path.join(DATA_DIR, "sample.flac")
    data = metadata.Metadata(path)

    with pytest.raises(metadata.TagNotFound):
        data.get("test")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2017", datetime.date(2017, 1, 1)),
        ("2017-12-31", datetime.date(2017, 12, 31)),
        ("2017-14-01 01:32", datetime.date(2017, 1, 14)),  # deezer format
        ("2017-02", datetime.date(2017, 1, 1)),  # weird format that exists
        ("0000", None),
        ("", None),
        ("nonsense", None),
    ],
)
def test_date_parsing(raw, expected):
    assert metadata.PermissiveDateField().to_internal_value(raw) == expected


def test_metadata_fallback_ogg_theora(mocker):
    path = os.path.join(DATA_DIR, "with_cover.ogg")
    data = metadata.Metadata(path)

    assert isinstance(data._file, mutagen.oggtheora.OggTheora)
    assert isinstance(data.fallback, metadata.Metadata)
    assert isinstance(data.fallback._file, mutagen.oggvorbis.OggVorbis)

    expected_result = data.fallback.get("pictures")
    fallback_get = mocker.spy(data.fallback, "get")

    assert expected_result is not None
    assert data.get("pictures", "default") == expected_result

    fallback_get.assert_called_once_with("pictures", "default")


@pytest.mark.parametrize(
    "path, expected",
    [
        (
            "test.mp3",
            {
                "title": "Bend",
                "artists": [
                    {
                        "name": "Binärpilot",
                        "mbid": uuid.UUID("9c6bddde-6228-4d9f-ad0d-03f6fcb19e13"),
                    },
                    {"name": "Another artist", "mbid": None},
                ],
                "album": {
                    "title": "You Can't Stop Da Funk",
                    "mbid": uuid.UUID("ce40cdb1-a562-4fd8-a269-9269f98d4124"),
                    "release_date": datetime.date(2006, 2, 7),
                    "artists": [
                        {
                            "name": "Binärpilot",
                            "mbid": uuid.UUID("9c6bddde-6228-4d9f-ad0d-03f6fcb19e13"),
                        },
                        {"name": "Another artist", "mbid": None},
                    ],
                },
                "position": 2,
                "disc_number": 1,
                "mbid": uuid.UUID("f269d497-1cc0-4ae4-a0c4-157ec7d73fcb"),
                "license": "https://creativecommons.org/licenses/by-nc-nd/2.5/",
                "copyright": "Someone",
                "tags": ["Funk"],
                "description": {"text": "Hello there", "content_type": "text/plain"},
            },
        ),
        (
            "test.ogg",
            {
                "title": "Peer Gynt Suite no. 1, op. 46: I. Morning",
                "artists": [
                    {
                        "name": "Edvard Grieg",
                        "mbid": uuid.UUID("013c8e5b-d72a-4cd3-8dee-6c64d6125823"),
                    },
                    {"name": "Musopen Symphony Orchestra", "mbid": None},
                ],
                "album": {
                    "title": "Peer Gynt Suite no. 1, op. 46",
                    "mbid": uuid.UUID("a766da8b-8336-47aa-a3ee-371cc41ccc75"),
                    "release_date": datetime.date(2012, 8, 15),
                    "artists": [
                        {
                            "name": "Edvard Grieg",
                            "mbid": uuid.UUID("013c8e5b-d72a-4cd3-8dee-6c64d6125823"),
                        },
                        {
                            "name": "Musopen Symphony Orchestra",
                            "mbid": uuid.UUID("5b4d7d2d-36df-4b38-95e3-a964234f520f"),
                        },
                    ],
                },
                "position": 1,
                "disc_number": 1,
                "mbid": uuid.UUID("bd21ac48-46d8-4e78-925f-d9cc2a294656"),
                "license": "Dummy license: http://creativecommons.org/licenses/by-sa/4.0/",
                "copyright": "Someone",
                "tags": ["Classical"],
                "description": {"text": "Hello there", "content_type": "text/plain"},
            },
        ),
        (
            "test.opus",
            {
                "title": "Peer Gynt Suite no. 1, op. 46: I. Morning",
                "artists": [
                    {
                        "name": "Edvard Grieg",
                        "mbid": uuid.UUID("013c8e5b-d72a-4cd3-8dee-6c64d6125823"),
                    },
                    {"name": "Musopen Symphony Orchestra", "mbid": None},
                ],
                "album": {
                    "title": "Peer Gynt Suite no. 1, op. 46",
                    "mbid": uuid.UUID("a766da8b-8336-47aa-a3ee-371cc41ccc75"),
                    "release_date": datetime.date(2012, 8, 15),
                    "artists": [
                        {
                            "name": "Edvard Grieg",
                            "mbid": uuid.UUID("013c8e5b-d72a-4cd3-8dee-6c64d6125823"),
                        },
                        {
                            "name": "Musopen Symphony Orchestra",
                            "mbid": uuid.UUID("5b4d7d2d-36df-4b38-95e3-a964234f520f"),
                        },
                    ],
                },
                "position": 1,
                "disc_number": 1,
                "mbid": uuid.UUID("bd21ac48-46d8-4e78-925f-d9cc2a294656"),
                "license": "Dummy license: http://creativecommons.org/licenses/by-sa/4.0/",
                "copyright": "Someone",
                "tags": ["Classical"],
                "description": {"text": "Hello there", "content_type": "text/plain"},
            },
        ),
        (
            "test_theora.ogg",
            {
                "title": "Drei Kreuze (dass wir hier sind)",
                "artists": [
                    {
                        "name": "Die Toten Hosen",
                        "mbid": uuid.UUID("c3bc80a6-1f4a-4e17-8cf0-6b1efe8302f1"),
                    }
                ],
                "album": {
                    "title": "Ballast der Republik",
                    "mbid": uuid.UUID("1f0441ad-e609-446d-b355-809c445773cf"),
                    "release_date": datetime.date(2012, 5, 4),
                    "artists": [
                        {
                            "name": "Die Toten Hosen",
                            "mbid": uuid.UUID("c3bc80a6-1f4a-4e17-8cf0-6b1efe8302f1"),
                        }
                    ],
                },
                "tags": ["Rock"],
                "position": 1,
                "disc_number": 1,
                "mbid": uuid.UUID("124d0150-8627-46bc-bc14-789a3bc960c8"),
                # somehow, I cannot successfully create an ogg theora file
                # with the proper license field
                # ("license", "Dummy license: http://creativecommons.org/licenses/by-sa/4.0/"),
                "copyright": "℗ 2012 JKP GmbH & Co. KG",
                "description": {"text": "Hello there", "content_type": "text/plain"},
            },
        ),
        (
            "sample.flac",
            {
                "title": "999,999",
                "artists": [
                    {
                        "name": "Nine Inch Nails",
                        "mbid": uuid.UUID("b7ffd2af-418f-4be2-bdd1-22f8b48613da"),
                    }
                ],
                "album": {
                    "title": "The Slip",
                    "mbid": uuid.UUID("12b57d46-a192-499e-a91f-7da66790a1c1"),
                    "release_date": datetime.date(2008, 5, 5),
                    "artists": [
                        {
                            "name": "Nine Inch Nails",
                            "mbid": uuid.UUID("b7ffd2af-418f-4be2-bdd1-22f8b48613da"),
                        }
                    ],
                },
                "position": 1,
                "disc_number": 1,
                "mbid": uuid.UUID("30f3f33e-8d0c-4e69-8539-cbd701d18f28"),
                "license": "http://creativecommons.org/licenses/by-nc-sa/3.0/us/",
                "copyright": "2008 nin",
                "tags": ["Industrial"],
                "description": {"text": "Hello there", "content_type": "text/plain"},
            },
        ),
    ],
)
def test_track_metadata_serializer(path, expected, mocker):
    path = os.path.join(DATA_DIR, path)
    data = metadata.Metadata(path)
    get_picture = mocker.patch.object(data, "get_picture")
    expected["album"]["cover_data"] = get_picture.return_value

    serializer = metadata.TrackMetadataSerializer(data=data)
    assert serializer.is_valid(raise_exception=True) is True
    assert serializer.validated_data == expected

    get_picture.assert_called_once_with("cover_front", "other")


@pytest.mark.parametrize(
    "raw, expected",
    [
        (
            {
                "names": "Hello; World",
                "mbids": "f269d497-1cc0-4ae4-a0c4-157ec7d73fcb; f269d497-1cc0-4ae4-a0c4-157ec7d73fcd ",
            },
            [
                {
                    "name": "Hello",
                    "mbid": uuid.UUID("f269d497-1cc0-4ae4-a0c4-157ec7d73fcb"),
                },
                {
                    "name": "World",
                    "mbid": uuid.UUID("f269d497-1cc0-4ae4-a0c4-157ec7d73fcd"),
                },
            ],
        ),
        (
            {
                "names": "Hello; World; Foo",
                "mbids": "f269d497-1cc0-4ae4-a0c4-157ec7d73fcb; f269d497-1cc0-4ae4-a0c4-157ec7d73fcd ",
            },
            [
                {
                    "name": "Hello",
                    "mbid": uuid.UUID("f269d497-1cc0-4ae4-a0c4-157ec7d73fcb"),
                },
                {
                    "name": "World",
                    "mbid": uuid.UUID("f269d497-1cc0-4ae4-a0c4-157ec7d73fcd"),
                },
                {"name": "Foo", "mbid": None},
            ],
        ),
    ],
)
def test_artists_cleaning(raw, expected):
    field = metadata.ArtistField()
    assert field.to_internal_value(raw) == expected


@pytest.mark.parametrize(
    "data, errored_field",
    [
        ({"name": "Hello", "mbid": "wrong-uuid"}, "mbid"),  # wrong uuid
        ({"name": "", "mbid": "f269d497-1cc0-4ae4-a0c4-157ec7d73fcd"}, "name"),
    ],
)
def test_artist_serializer_validation(data, errored_field):
    serializer = metadata.ArtistSerializer(data=data)
    assert serializer.is_valid() is False

    assert len(serializer.errors) == 1
    assert errored_field in serializer.errors


@pytest.mark.parametrize(
    "data, errored_field",
    [
        ({"title": "Hello", "mbid": "wrong"}, "mbid"),  # wrong uuid
        (
            {"title": "", "mbid": "f269d497-1cc0-4ae4-a0c4-157ec7d73fcd"},
            "title",
        ),  # empty title
    ],
)
def test_album_serializer_validation(data, errored_field):
    serializer = metadata.AlbumSerializer(data=data)
    assert serializer.is_valid() is False

    assert len(serializer.errors) == 1
    assert errored_field in serializer.errors


def test_fake_metadata_with_serializer():
    data = {
        "title": "Peer Gynt Suite no. 1, op. 46: I. Morning",
        "artist": "Edvard Grieg",
        "album_artist": "Edvard Grieg; Musopen Symphony Orchestra",
        "album": "Peer Gynt Suite no. 1, op. 46",
        "date": "2012-08-15",
        "position": "1",
        "disc_number": "1",
        "musicbrainz_albumid": "a766da8b-8336-47aa-a3ee-371cc41ccc75",
        "mbid": "bd21ac48-46d8-4e78-925f-d9cc2a294656",
        "musicbrainz_artistid": "013c8e5b-d72a-4cd3-8dee-6c64d6125823",
        "musicbrainz_albumartistid": "013c8e5b-d72a-4cd3-8dee-6c64d6125823;5b4d7d2d-36df-4b38-95e3-a964234f520f",
        "license": "Dummy license: http://creativecommons.org/licenses/by-sa/4.0/",
        "copyright": "Someone",
        "comment": "hello there",
    }

    expected = {
        "title": "Peer Gynt Suite no. 1, op. 46: I. Morning",
        "description": {"text": "hello there", "content_type": "text/plain"},
        "artists": [
            {
                "name": "Edvard Grieg",
                "mbid": uuid.UUID("013c8e5b-d72a-4cd3-8dee-6c64d6125823"),
            }
        ],
        "album": {
            "title": "Peer Gynt Suite no. 1, op. 46",
            "mbid": uuid.UUID("a766da8b-8336-47aa-a3ee-371cc41ccc75"),
            "release_date": datetime.date(2012, 8, 15),
            "artists": [
                {
                    "name": "Edvard Grieg",
                    "mbid": uuid.UUID("013c8e5b-d72a-4cd3-8dee-6c64d6125823"),
                },
                {
                    "name": "Musopen Symphony Orchestra",
                    "mbid": uuid.UUID("5b4d7d2d-36df-4b38-95e3-a964234f520f"),
                },
            ],
            "cover_data": None,
        },
        "position": 1,
        "disc_number": 1,
        "mbid": uuid.UUID("bd21ac48-46d8-4e78-925f-d9cc2a294656"),
        "license": "Dummy license: http://creativecommons.org/licenses/by-sa/4.0/",
        "copyright": "Someone",
    }
    serializer = metadata.TrackMetadataSerializer(data=metadata.FakeMetadata(data))
    assert serializer.is_valid(raise_exception=True) is True
    assert serializer.validated_data == expected


def test_serializer_album_artist_missing():
    data = {
        "title": "Peer Gynt Suite no. 1, op. 46: I. Morning",
        "artist": "Edvard Grieg",
        "album": "Peer Gynt Suite no. 1, op. 46",
    }

    expected = {
        "title": "Peer Gynt Suite no. 1, op. 46: I. Morning",
        "artists": [{"name": "Edvard Grieg", "mbid": None}],
        "album": {
            "title": "Peer Gynt Suite no. 1, op. 46",
            "mbid": None,
            "release_date": None,
            "artists": [],
            "cover_data": None,
        },
    }
    serializer = metadata.TrackMetadataSerializer(data=metadata.FakeMetadata(data))
    assert serializer.is_valid(raise_exception=True) is True
    assert serializer.validated_data == expected


@pytest.mark.parametrize(
    "data",
    [
        # no album tag
        {"title": "Track", "artist": "Artist"},
        # empty/null values
        {"title": "Track", "artist": "Artist", "album": ""},
        {"title": "Track", "artist": "Artist", "album": " "},
        {"title": "Track", "artist": "Artist", "album": None},
    ],
)
def test_serializer_album_default_title_when_missing_or_empty(data):
    expected = {
        "title": "Track",
        "artists": [{"name": "Artist", "mbid": None}],
        "album": {
            "title": metadata.UNKNOWN_ALBUM,
            "mbid": None,
            "release_date": None,
            "artists": [],
            "cover_data": None,
        },
    }
    serializer = metadata.TrackMetadataSerializer(data=metadata.FakeMetadata(data))
    assert serializer.is_valid(raise_exception=True) is True
    assert serializer.validated_data == expected


@pytest.mark.parametrize(
    "field_name", ["copyright", "license", "mbid", "position", "disc_number"]
)
def test_serializer_empty_fields(field_name):
    data = {
        "title": "Track Title",
        "artist": "Track Artist",
        "album": "Track Album",
        # empty copyright/license field shouldn't fail, cf #850
        field_name: "",
    }
    expected = {
        "title": "Track Title",
        "artists": [{"name": "Track Artist", "mbid": None}],
        "album": {
            "title": "Track Album",
            "mbid": None,
            "release_date": None,
            "artists": [],
            "cover_data": None,
        },
    }
    serializer = metadata.TrackMetadataSerializer(data=metadata.FakeMetadata(data))
    assert serializer.is_valid(raise_exception=True) is True
    assert serializer.validated_data == expected


def test_serializer_strict_mode_false():
    data = {}
    expected = {
        "artists": [{"name": None, "mbid": None}],
        "album": {
            "title": "[Unknown Album]",
            "mbid": None,
            "release_date": None,
            "artists": [],
            "cover_data": None,
        },
    }
    serializer = metadata.TrackMetadataSerializer(
        data=metadata.FakeMetadata(data), context={"strict": False}
    )
    assert serializer.is_valid(raise_exception=True) is True
    assert serializer.validated_data == expected


def test_serializer_strict_mode_true():
    data = {}
    serializer = metadata.TrackMetadataSerializer(
        data=metadata.FakeMetadata(data), context={"strict": True}
    )
    with pytest.raises(metadata.serializers.ValidationError):
        assert serializer.is_valid(raise_exception=True)


def test_artist_field_featuring():
    data = {
        "artist": "Santana feat. Chris Cornell",
        # here is the tricky bit, note the slash
        "musicbrainz_artistid": "9a3bf45c-347d-4630-894d-7cf3e8e0b632/cbf9738d-8f81-4a92-bc64-ede09341652d",
    }

    expected = [{"name": "Santana feat. Chris Cornell", "mbid": None}]

    field = metadata.ArtistField()
    value = field.get_value(data)

    assert field.to_internal_value(value) == expected


@pytest.mark.parametrize(
    "genre, expected_tags",
    [
        ("Pop", ["Pop"]),
        ("pop", ["pop"]),
        ("Pop-Rock", ["PopRock"]),
        ("Pop - Rock", ["Pop", "Rock"]),
        ("Soundtrack - Cute Anime", ["Soundtrack", "CuteAnime"]),
        ("Pop, Rock", ["Pop", "Rock"]),
        ("Chanson française", ["ChansonFrançaise"]),
        ("Unhandled❤️", []),
        ("tag with non-breaking spaces", []),
    ],
)
def test_acquire_tags_from_genre(genre, expected_tags):
    data = {
        "title": "Track Title",
        "artist": "Track Artist",
        "album": "Track Album",
        "genre": genre,
    }
    expected = {
        "title": "Track Title",
        "artists": [{"name": "Track Artist", "mbid": None}],
        "album": {
            "title": "Track Album",
            "mbid": None,
            "release_date": None,
            "artists": [],
            "cover_data": None,
        },
    }
    if expected_tags:
        expected["tags"] = expected_tags

    serializer = metadata.TrackMetadataSerializer(data=metadata.FakeMetadata(data))
    assert serializer.is_valid(raise_exception=True) is True
    assert serializer.validated_data == expected

import pytest

from funkwhale_api.music import filters
from funkwhale_api.music import models


def test_album_filter_hidden(factories, mocker, queryset_equal_list):
    factories["music.Album"]()
    cf = factories["moderation.UserFilter"](for_artist=True)
    hidden_album = factories["music.Album"](artist=cf.target_artist)

    qs = models.Album.objects.all()
    filterset = filters.AlbumFilter(
        {"hidden": "true"}, request=mocker.Mock(user=cf.user), queryset=qs
    )

    assert filterset.qs == [hidden_album]


def test_artist_filter_hidden(factories, mocker, queryset_equal_list):
    factories["music.Artist"]()
    cf = factories["moderation.UserFilter"](for_artist=True)
    hidden_artist = cf.target_artist

    qs = models.Artist.objects.all()
    filterset = filters.ArtistFilter(
        {"hidden": "true"}, request=mocker.Mock(user=cf.user), queryset=qs
    )

    assert filterset.qs == [hidden_artist]


def test_artist_filter_track_artist(factories, mocker, queryset_equal_list):
    factories["music.Track"]()
    cf = factories["moderation.UserFilter"](for_artist=True)
    hidden_track = factories["music.Track"](artist=cf.target_artist)

    qs = models.Track.objects.all()
    filterset = filters.TrackFilter(
        {"hidden": "true"}, request=mocker.Mock(user=cf.user), queryset=qs
    )

    assert filterset.qs == [hidden_track]


def test_artist_filter_track_album_artist(factories, mocker, queryset_equal_list):
    factories["music.Track"]()
    cf = factories["moderation.UserFilter"](for_artist=True)
    hidden_track = factories["music.Track"](album__artist=cf.target_artist)

    qs = models.Track.objects.all()
    filterset = filters.TrackFilter(
        {"hidden": "true"}, request=mocker.Mock(user=cf.user), queryset=qs
    )

    assert filterset.qs == [hidden_track]


@pytest.mark.parametrize(
    "factory_name, filterset_class",
    [
        ("music.Track", filters.TrackFilter),
        ("music.Artist", filters.ArtistFilter),
        ("music.Album", filters.AlbumFilter),
    ],
)
def test_track_filter_tag_single(
    factory_name,
    filterset_class,
    factories,
    mocker,
    queryset_equal_list,
    anonymous_user,
):
    factories[factory_name]()
    # tag name partially match the query, so this shouldn't match
    factories[factory_name](set_tags=["TestTag1"])
    tagged = factories[factory_name](set_tags=["TestTag"])
    qs = tagged.__class__.objects.all()
    filterset = filterset_class(
        {"tag": "testTaG"}, request=mocker.Mock(user=anonymous_user), queryset=qs
    )

    assert filterset.qs == [tagged]


@pytest.mark.parametrize(
    "factory_name, filterset_class",
    [
        ("music.Track", filters.TrackFilter),
        ("music.Artist", filters.ArtistFilter),
        ("music.Album", filters.AlbumFilter),
    ],
)
def test_track_filter_tag_multiple(
    factory_name,
    filterset_class,
    factories,
    mocker,
    queryset_equal_list,
    anonymous_user,
):
    factories[factory_name](set_tags=["TestTag1"])
    tagged = factories[factory_name](set_tags=["TestTag1", "TestTag2"])
    qs = tagged.__class__.objects.all()
    filterset = filterset_class(
        {"tag": ["testTaG1", "TestTag2"]},
        request=mocker.Mock(user=anonymous_user),
        queryset=qs,
    )

    assert filterset.qs == [tagged]


def test_channel_filter_track(factories, queryset_equal_list, mocker, anonymous_user):
    channel = factories["audio.Channel"](library__privacy_level="everyone")
    upload = factories["music.Upload"](
        library=channel.library, playable=True, track__artist=channel.artist
    )
    factories["music.Track"]()
    qs = upload.track.__class__.objects.all()
    filterset = filters.TrackFilter(
        {"channel": channel.uuid, "include_channels": "true"},
        request=mocker.Mock(user=anonymous_user, actor=None),
        queryset=qs,
    )

    assert filterset.qs == [upload.track]


def test_channel_filter_album(factories, queryset_equal_list, mocker, anonymous_user):
    channel = factories["audio.Channel"](library__privacy_level="everyone")
    upload = factories["music.Upload"](
        library=channel.library, playable=True, track__artist=channel.artist
    )
    factories["music.Album"]()
    qs = upload.track.album.__class__.objects.all()
    filterset = filters.AlbumFilter(
        {"channel": channel.uuid, "include_channels": "true"},
        request=mocker.Mock(user=anonymous_user, actor=None),
        queryset=qs,
    )

    assert filterset.qs == [upload.track.album]


def test_library_filter_track(factories, queryset_equal_list, mocker, anonymous_user):
    library = factories["music.Library"](privacy_level="everyone")
    upload = factories["music.Upload"](library=library, playable=True)
    factories["music.Track"]()
    qs = upload.track.__class__.objects.all()
    filterset = filters.TrackFilter(
        {"library": library.uuid},
        request=mocker.Mock(user=anonymous_user, actor=None),
        queryset=qs,
    )

    assert filterset.qs == [upload.track]


def test_library_filter_album(factories, queryset_equal_list, mocker, anonymous_user):
    library = factories["music.Library"](privacy_level="everyone")
    upload = factories["music.Upload"](library=library, playable=True)
    factories["music.Album"]()
    qs = upload.track.album.__class__.objects.all()
    filterset = filters.AlbumFilter(
        {"library": library.uuid},
        request=mocker.Mock(user=anonymous_user, actor=None),
        queryset=qs,
    )

    assert filterset.qs == [upload.track.album]


def test_library_filter_artist(factories, queryset_equal_list, mocker, anonymous_user):
    library = factories["music.Library"](privacy_level="everyone")
    upload = factories["music.Upload"](library=library, playable=True)
    factories["music.Artist"]()
    qs = upload.track.artist.__class__.objects.all()
    filterset = filters.ArtistFilter(
        {"library": library.uuid},
        request=mocker.Mock(user=anonymous_user, actor=None),
        queryset=qs,
    )

    assert filterset.qs == [upload.track.artist]


def test_track_filter_artist_includes_album_artist(
    factories, mocker, queryset_equal_list, anonymous_user
):
    factories["music.Track"]()
    track1 = factories["music.Track"]()
    track2 = factories["music.Track"](
        album__artist=track1.artist, artist=factories["music.Artist"]()
    )

    qs = models.Track.objects.all()
    filterset = filters.TrackFilter(
        {"artist": track1.artist.pk},
        request=mocker.Mock(user=anonymous_user),
        queryset=qs,
    )

    assert filterset.qs == [track2, track1]


@pytest.mark.parametrize(
    "factory_name, filterset_class",
    [
        ("music.Track", filters.TrackFilter),
        ("music.Artist", filters.ArtistFilter),
        ("music.Album", filters.AlbumFilter),
    ],
)
def test_filter_tag_related(
    factory_name,
    filterset_class,
    factories,
    anonymous_user,
    queryset_equal_list,
    mocker,
):
    factories["tags.Tag"](name="foo")
    factories["tags.Tag"](name="bar")
    factories["tags.Tag"](name="baz")
    factories["tags.Tag"]()
    factories["tags.Tag"]()

    matches = [
        factories[factory_name](set_tags=["foo", "bar", "baz", "noop"]),
        factories[factory_name](set_tags=["foo", "baz", "noop"]),
        factories[factory_name](set_tags=["baz", "noop"]),
    ]
    factories[factory_name](set_tags=["noop"]),
    obj = factories[factory_name](set_tags=["foo", "bar", "baz"])

    filterset = filterset_class(
        {"related": obj.pk, "ordering": "-related"},
        request=mocker.Mock(user=anonymous_user, actor=None),
        queryset=obj.__class__.objects.all(),
    )
    assert filterset.qs == matches

import io
import pytest

from funkwhale_api.common import utils


def test_chunk_queryset(factories):
    actors = factories["federation.Actor"].create_batch(size=4)
    queryset = actors[0].__class__.objects.all()
    chunks = list(utils.chunk_queryset(queryset, 2))

    assert list(chunks[0]) == actors[0:2]
    assert list(chunks[1]) == actors[2:4]


def test_update_prefix(factories):
    actors = []
    fid = "http://hello.world/actor/{}/"
    for i in range(3):
        actors.append(factories["federation.Actor"](fid=fid.format(i)))
    noop = [
        factories["federation.Actor"](fid="https://hello.world/actor/witness/"),
        factories["federation.Actor"](fid="http://another.world/actor/witness/"),
        factories["federation.Actor"](fid="http://foo.bar/actor/witness/"),
    ]

    qs = actors[0].__class__.objects.filter(fid__startswith="http://hello.world")
    assert qs.count() == 3

    result = utils.replace_prefix(
        actors[0].__class__.objects.all(),
        "fid",
        "http://hello.world",
        "https://hello.world",
    )

    assert result == 3

    for n in noop:
        old = n.fid
        n.refresh_from_db()
        assert old == n.fid

    for n in actors:
        old = n.fid
        n.refresh_from_db()
        assert n.fid == old.replace("http://", "https://")


@pytest.mark.parametrize(
    "conf, mock_args, data, expected",
    [
        (
            ["field1", "field2"],
            {"field1": "foo", "field2": "test"},
            {"field1": "bar"},
            {"field1": "bar"},
        ),
        (
            ["field1", "field2"],
            {"field1": "foo", "field2": "test"},
            {"field1": "foo"},
            {},
        ),
        (
            ["field1", "field2"],
            {"field1": "foo", "field2": "test"},
            {"field1": "foo", "field2": "test"},
            {},
        ),
        (
            ["field1", "field2"],
            {"field1": "foo", "field2": "test"},
            {"field1": "bar", "field2": "test1"},
            {"field1": "bar", "field2": "test1"},
        ),
        (
            [("field1", "Hello"), ("field2", "World")],
            {"Hello": "foo", "World": "test"},
            {"field1": "bar", "field2": "test1"},
            {"Hello": "bar", "World": "test1"},
        ),
    ],
)
def test_get_updated_fields(conf, mock_args, data, expected, mocker):
    obj = mocker.Mock(**mock_args)

    assert utils.get_updated_fields(conf, data, obj) == expected


@pytest.mark.parametrize(
    "start, end, expected",
    [
        ("https://domain", "/api", "https://domain/api"),
        ("https://domain/", "/api", "https://domain/api"),
        ("https://domain", "api", "https://domain/api"),
        ("https://domain", "https://api", "https://api"),
        ("https://domain", "http://api", "http://api"),
    ],
)
def test_join_url(start, end, expected):
    assert utils.join_url(start, end) == expected


@pytest.mark.parametrize(
    "text, content_type, permissive, expected",
    [
        ("hello world", "text/markdown", False, "<p>hello world</p>"),
        ("hello world", "text/plain", False, "<p>hello world</p>"),
        (
            "<strong>hello world</strong>",
            "text/html",
            False,
            "<strong>hello world</strong>",
        ),
        # images and other non whitelisted html should be removed
        ("hello world\n![img](src)", "text/markdown", False, "<p>hello world</p>"),
        (
            "hello world\n\n<script></script>\n\n<style></style>",
            "text/markdown",
            False,
            "<p>hello world</p>",
        ),
        (
            "<p>hello world</p><script></script>\n\n<style></style>",
            "text/html",
            False,
            "<p>hello world</p>",
        ),
        (
            '<p class="foo">hello world</p><script></script>\n\n<style></style>',
            "text/markdown",
            True,
            '<p class="foo">hello world</p>',
        ),
    ],
)
def test_render_html(text, content_type, permissive, expected):
    result = utils.render_html(text, content_type, permissive=permissive)
    assert result == expected


def test_attach_file_url(factories):
    album = factories["music.Album"](with_cover=True)
    existing_attachment = album.attachment_cover
    assert existing_attachment is not None

    data = {"mimetype": "image/jpeg", "url": "https://example.com/test.jpg"}
    new_attachment = utils.attach_file(album, "attachment_cover", data)

    album.refresh_from_db()

    with pytest.raises(existing_attachment.DoesNotExist):
        existing_attachment.refresh_from_db()

    assert album.attachment_cover == new_attachment
    assert not new_attachment.file
    assert new_attachment.url == data["url"]
    assert new_attachment.mimetype == data["mimetype"]


def test_attach_file_url_fetch(factories, r_mock):
    album = factories["music.Album"](with_cover=True)

    data = {"mimetype": "image/jpeg", "url": "https://example.com/test.jpg"}
    r_mock.get(data["url"], body=io.BytesIO(b"content"))
    new_attachment = utils.attach_file(album, "attachment_cover", data, fetch=True)

    album.refresh_from_db()

    assert album.attachment_cover == new_attachment
    assert new_attachment.file.read() == b"content"
    assert new_attachment.url == data["url"]
    assert new_attachment.mimetype == data["mimetype"]


def test_attach_file_attachment(factories, r_mock):
    album = factories["music.Album"]()

    data = factories["common.Attachment"]()
    utils.attach_file(album, "attachment_cover", data)

    album.refresh_from_db()

    assert album.attachment_cover == data


def test_attach_file_content(factories, r_mock):
    album = factories["music.Album"]()

    data = {"mimetype": "image/jpeg", "content": b"content"}
    new_attachment = utils.attach_file(album, "attachment_cover", data)

    album.refresh_from_db()

    assert album.attachment_cover == new_attachment
    assert new_attachment.file.read() == b"content"
    assert new_attachment.url is None
    assert new_attachment.mimetype == data["mimetype"]


@pytest.mark.parametrize(
    "ignore, hostname, protocol, meta, path, expected",
    [
        (
            False,
            "test.hostname",
            "http",
            {
                "HTTP_X_FORWARDED_HOST": "real.hostname",
                "HTTP_X_FORWARDED_PROTO": "https",
            },
            "/hello",
            "https://real.hostname/hello",
        ),
        (
            False,
            "test.hostname",
            "http",
            {
                "HTTP_X_FORWARDED_HOST": "real.hostname",
                "HTTP_X_FORWARDED_PROTO": "http",
            },
            "/hello",
            "http://real.hostname/hello",
        ),
        (
            True,
            "test.hostname",
            "http",
            {
                "HTTP_X_FORWARDED_HOST": "real.hostname",
                "HTTP_X_FORWARDED_PROTO": "https",
            },
            "/hello",
            "http://test.hostname/hello",
        ),
        (
            True,
            "test.hostname",
            "https",
            {
                "HTTP_X_FORWARDED_HOST": "real.hostname",
                "HTTP_X_FORWARDED_PROTO": "http",
            },
            "/hello",
            "https://test.hostname/hello",
        ),
    ],
)
def test_monkey_patch_request_build_absolute_uri(
    ignore, hostname, protocol, meta, path, expected, fake_request, settings
):
    settings.IGNORE_FORWARDED_HOST_AND_PROTO = ignore
    settings.ALLOWED_HOSTS = "*"
    settings.FUNKWHALE_HOSTNAME = hostname
    settings.FUNKWHALE_PROTOCOL = protocol
    request = fake_request.get("/", **meta)

    assert request.build_absolute_uri(path) == expected

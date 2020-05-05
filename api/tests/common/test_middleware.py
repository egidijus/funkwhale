import html
import time
import pytest
from django.http import HttpResponse
from django.urls import reverse

from funkwhale_api.federation import utils as federation_utils

from funkwhale_api.common import middleware
from funkwhale_api.common import throttling
from funkwhale_api.common import utils


def test_spa_fallback_middleware_no_404(mocker):
    get_response = mocker.Mock()
    get_response.return_value = mocker.Mock(status_code=200)
    request = mocker.Mock(path="/")
    m = middleware.SPAFallbackMiddleware(get_response)

    assert m(request) == get_response.return_value


def test_spa_middleware_calls_should_fallback_false(mocker):
    get_response = mocker.Mock()
    get_response.return_value = mocker.Mock(status_code=404)
    should_falback = mocker.patch.object(
        middleware, "should_fallback_to_spa", return_value=False
    )
    request = mocker.Mock(path="/")

    m = middleware.SPAFallbackMiddleware(get_response)

    assert m(request) == get_response.return_value
    should_falback.assert_called_once_with(request.path)


def test_spa_middleware_should_fallback_true(mocker):
    get_response = mocker.Mock()
    get_response.return_value = mocker.Mock(status_code=404)
    request = mocker.Mock(path="/")
    mocker.patch.object(middleware, "should_fallback_to_spa", return_value=True)
    serve_spa = mocker.patch.object(middleware, "serve_spa")
    m = middleware.SPAFallbackMiddleware(get_response)

    assert m(request) == serve_spa.return_value
    serve_spa.assert_called_once_with(request)


@pytest.mark.parametrize(
    "path,expected",
    [("/", True), ("/federation", False), ("/api", False), ("/an/spa/path/", True)],
)
def test_should_fallback(path, expected, mocker):
    assert middleware.should_fallback_to_spa(path) is expected


def test_serve_spa_from_cache(mocker, settings, preferences, no_api_auth):
    preferences["instance__name"] = 'Best Funkwhale "pod"'
    request = mocker.Mock(path="/")
    get_spa_html = mocker.patch.object(
        middleware,
        "get_spa_html",
        return_value="<html><head><title>Funkwhale</title></head></html>",
    )
    mocker.patch.object(
        middleware,
        "get_default_head_tags",
        return_value=[
            {"tag": "meta", "property": "og:title", "content": "default title"},
            {"tag": "meta", "property": "og:site_name", "content": "default site name"},
        ],
    )
    get_request_head_tags = mocker.patch.object(
        middleware,
        "get_request_head_tags",
        return_value=[
            {"tag": "meta", "property": "og:title", "content": "custom title"},
            {
                "tag": "meta",
                "property": "og:description",
                "content": "custom description",
            },
        ],
    )
    response = middleware.serve_spa(request)

    assert response.status_code == 200
    expected = [
        "<html><head>"
        "<title>{}</title>".format(html.escape(preferences["instance__name"])),
        '<meta content="custom title" property="og:title" />',
        '<meta content="custom description" property="og:description" />',
        '<meta content="default site name" property="og:site_name" />',
        "</head></html>",
    ]
    get_spa_html.assert_called_once_with(settings.FUNKWHALE_SPA_HTML_ROOT)
    get_request_head_tags.assert_called_once_with(request)
    assert response.content == "\n".join(expected).encode()


def test_get_default_head_tags(preferences, settings):
    settings.APP_NAME = "Funkwhale"
    preferences["instance__name"] = "Hello"
    preferences["instance__short_description"] = "World"

    expected = [
        {"tag": "meta", "property": "og:type", "content": "website"},
        {"tag": "meta", "property": "og:site_name", "content": "Hello - Funkwhale"},
        {"tag": "meta", "property": "og:description", "content": "World"},
        {
            "tag": "meta",
            "property": "og:image",
            "content": settings.FUNKWHALE_URL + "/front/favicon.png",
        },
        {"tag": "meta", "property": "og:url", "content": settings.FUNKWHALE_URL + "/"},
    ]

    assert middleware.get_default_head_tags("/") == expected


def test_get_spa_html_from_cache(local_cache):
    local_cache.set("spa-file:http://test:index.html", "hello world")

    assert middleware.get_spa_html("http://test") == "hello world"


def test_get_spa_html_from_http(local_cache, r_mock, mocker, settings):
    cache_set = mocker.spy(local_cache, "set")
    url = "http://test"
    r_mock.get(url + "/index.html", text="hello world")

    assert middleware.get_spa_html("http://test") == "hello world"
    cache_set.assert_called_once_with(
        "spa-file:{}:index.html".format(url),
        "hello world",
        settings.FUNKWHALE_SPA_HTML_CACHE_DURATION,
    )


def test_get_spa_html_from_disk(tmp_path):
    index = tmp_path / "index.html"
    index.write_bytes(b"hello world")
    assert middleware.get_spa_html(str(index)) == "hello world"


def test_get_route_head_tags(mocker, settings):
    match = mocker.Mock(args=[], kwargs={"pk": 42}, func=mocker.Mock())
    resolve = mocker.patch("django.urls.resolve", return_value=match)
    request = mocker.Mock(path="/tracks/42", headers={})
    tags = middleware.get_request_head_tags(request)

    assert tags == match.func.return_value
    match.func.assert_called_once_with(request, *[], redirect_to_ap=False, **{"pk": 42})
    resolve.assert_called_once_with(request.path, urlconf=settings.SPA_URLCONF)


def test_serve_spa_includes_custom_css(mocker, no_api_auth):
    request = mocker.Mock(path="/")
    mocker.patch.object(
        middleware,
        "get_spa_html",
        return_value="<html><head></head><body></body></html>",
    )
    mocker.patch.object(middleware, "get_default_head_tags", return_value=[])
    mocker.patch.object(middleware, "get_request_head_tags", return_value=[])
    get_custom_css = mocker.patch.object(
        middleware, "get_custom_css", return_value="body { background: black; }"
    )
    response = middleware.serve_spa(request)

    assert response.status_code == 200
    expected = [
        "<html><head>\n\n</head><body>",
        "<style>body { background: black; }</style>",
        "</body></html>",
    ]
    get_custom_css.assert_called_once_with()
    assert response.content == "\n".join(expected).encode()


@pytest.mark.parametrize(
    "custom_css, expected",
    [
        ("body { background: black; }", "body { background: black; }"),
        (
            "body { injection: </style> & Hello",
            "body { injection: &lt;/style&gt; &amp; Hello",
        ),
        (
            'body { background: url("image/url"); }',
            'body { background: url("image/url"); }',
        ),
    ],
)
def test_get_custom_css(preferences, custom_css, expected):
    preferences["ui__custom_css"] = custom_css

    assert middleware.get_custom_css() == expected


def test_throttle_status_middleware_includes_info_in_response_headers(mocker):
    get_response = mocker.Mock()
    response = HttpResponse()
    get_response.return_value = response
    request = mocker.Mock(
        path="/",
        _api_request=mocker.Mock(
            _throttle_status={
                "num_requests": 42,
                "duration": 3600,
                "scope": "hello",
                "history": [time.time() - 1600, time.time() - 1800],
            }
        ),
    )
    m = middleware.ThrottleStatusMiddleware(get_response)

    assert m(request) == response
    assert response["X-RateLimit-Limit"] == "42"
    assert response["X-RateLimit-Remaining"] == "40"
    assert response["X-RateLimit-Duration"] == "3600"
    assert response["X-RateLimit-Scope"] == "hello"
    assert response["X-RateLimit-Reset"] == str(int(time.time()) + 2000)
    assert response["X-RateLimit-ResetSeconds"] == str(2000)
    assert response["Retry-After"] == str(1800)


def test_throttle_status_middleware_returns_proper_response(mocker):
    get_response = mocker.Mock(side_effect=throttling.TooManyRequests())
    request = mocker.Mock(path="/", _api_request=None, _throttle_status=None)
    m = middleware.ThrottleStatusMiddleware(get_response)

    response = m(request)
    assert response.status_code == 429


@pytest.mark.parametrize(
    "link, new_url, expected",
    [
        (
            "<link rel=manifest href=/manifest.json>",
            "custom_url",
            '<link rel=manifest href="custom_url">',
        ),
        (
            "<link href=/manifest.json rel=manifest>",
            "custom_url",
            '<link rel=manifest href="custom_url">',
        ),
        (
            '<link href="/manifest.json" rel=manifest>',
            "custom_url",
            '<link rel=manifest href="custom_url">',
        ),
        (
            '<link href=/manifest.json rel="manifest">',
            "custom_url",
            '<link rel=manifest href="custom_url">',
        ),
        (
            "<link href='/manifest.json' rel=manifest>",
            "custom_url",
            '<link rel=manifest href="custom_url">',
        ),
        (
            "<link href=/manifest.json rel='manifest'>",
            "custom_url",
            '<link rel=manifest href="custom_url">',
        ),
        # not matching
        (
            "<link href=/manifest.json rel=notmanifest>",
            "custom_url",
            "<link href=/manifest.json rel=notmanifest>",
        ),
    ],
)
def test_rewrite_manifest_json_url(link, new_url, expected, mocker, settings):
    settings.FUNKWHALE_SPA_REWRITE_MANIFEST = True
    settings.FUNKWHALE_SPA_REWRITE_MANIFEST_URL = new_url
    spa_html = "<html><head><link rel=before>{}<link rel=after></head></html>".format(
        link
    )
    request = mocker.Mock(path="/")
    mocker.patch.object(middleware, "get_spa_html", return_value=spa_html)
    mocker.patch.object(
        middleware, "get_default_head_tags", return_value=[],
    )
    response = middleware.serve_spa(request)

    assert response.status_code == 200
    expected_html = "<html><head><link rel=before>{}<link rel=after>\n\n</head></html>".format(
        expected
    )
    assert response.content == expected_html.encode()


def test_rewrite_manifest_json_url_rewrite_disabled(mocker, settings):
    settings.FUNKWHALE_SPA_REWRITE_MANIFEST = False
    settings.FUNKWHALE_SPA_REWRITE_MANIFEST_URL = "custom_url"
    spa_html = "<html><head><link href=/manifest.json rel=manifest></head></html>"
    request = mocker.Mock(path="/")
    mocker.patch.object(middleware, "get_spa_html", return_value=spa_html)
    mocker.patch.object(
        middleware, "get_default_head_tags", return_value=[],
    )
    response = middleware.serve_spa(request)

    assert response.status_code == 200
    expected_html = (
        "<html><head><link href=/manifest.json rel=manifest>\n\n</head></html>"
    )
    assert response.content == expected_html.encode()


def test_rewrite_manifest_json_url_rewrite_default_url(mocker, settings):
    settings.FUNKWHALE_SPA_REWRITE_MANIFEST = True
    settings.FUNKWHALE_SPA_REWRITE_MANIFEST_URL = None
    spa_html = "<html><head><link href=/manifest.json rel=manifest></head></html>"
    expected_url = federation_utils.full_url(reverse("api:v1:instance:spa-manifest"))
    request = mocker.Mock(path="/")
    mocker.patch.object(middleware, "get_spa_html", return_value=spa_html)
    mocker.patch.object(
        middleware, "get_default_head_tags", return_value=[],
    )
    response = middleware.serve_spa(request)

    assert response.status_code == 200
    expected_html = '<html><head><link rel=manifest href="{}">\n\n</head></html>'.format(
        expected_url
    )
    assert response.content == expected_html.encode()


def test_spa_middleware_handles_api_redirect(mocker):
    get_response = mocker.Mock(return_value=mocker.Mock(status_code=404))
    redirect_url = "/test"
    mocker.patch.object(
        middleware, "serve_spa", side_effect=middleware.ApiRedirect(redirect_url)
    )
    api_view = mocker.Mock()
    match = mocker.Mock(args=["hello"], kwargs={"foo": "bar"}, func=api_view)
    mocker.patch.object(middleware.urls, "resolve", return_value=match)

    request = mocker.Mock(path="/")

    m = middleware.SPAFallbackMiddleware(get_response)

    response = m(request)

    api_view.assert_called_once_with(request, "hello", foo="bar")
    assert response == api_view.return_value


@pytest.mark.parametrize(
    "accept_header, expected",
    [
        ("text/html", False),
        ("application/activity+json", True),
        ("", False),
        ("noop", False),
        ("text/html,application/activity+json", False),
        ("application/activity+json,text/html", True),
    ],
)
def test_get_request_head_tags_calls_view_with_proper_arg_when_accept_header_set(
    accept_header, expected, mocker, fake_request
):
    request = fake_request.get("/", HTTP_ACCEPT=accept_header)

    view = mocker.Mock()
    match = mocker.Mock(args=["hello"], kwargs={"foo": "bar"}, func=view)
    mocker.patch.object(middleware.urls, "resolve", return_value=match)

    assert middleware.get_request_head_tags(request) == view.return_value
    view.assert_called_once_with(request, "hello", foo="bar", redirect_to_ap=expected)


@pytest.mark.parametrize(
    "factory_name, factory_kwargs, route_name, route_arg_name, route_arg",
    [
        (
            "federation.Actor",
            {"local": True},
            "actor_detail",
            "username",
            "preferred_username",
        ),
        (
            "audio.Channel",
            {"local": True},
            "channel_detail",
            "username",
            "actor.preferred_username",
        ),
        ("music.Artist", {}, "library_artist", "pk", "pk",),
        ("music.Album", {}, "library_album", "pk", "pk",),
        ("music.Track", {}, "library_track", "pk", "pk",),
        ("music.Library", {}, "library_library", "uuid", "uuid",),
        # when a track as a public upload, we should redirect to the upload instead
        ("music.Upload", {"playable": True}, "library_track", "pk", "track.pk"),
    ],
)
def test_spa_views_raise_api_redirect_when_accept_json_set(
    factory_name,
    factory_kwargs,
    route_name,
    route_arg_name,
    route_arg,
    factories,
    fake_request,
):
    obj = factories[factory_name](**factory_kwargs)
    url = utils.spa_reverse(
        route_name, kwargs={route_arg_name: utils.recursive_getattr(obj, route_arg)}
    )
    request = fake_request.get(url, HTTP_ACCEPT="application/activity+json")

    with pytest.raises(middleware.ApiRedirect) as excinfo:
        middleware.get_request_head_tags(request)
    assert excinfo.value.url == obj.fid

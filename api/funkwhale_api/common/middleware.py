import html
import logging
import io
import os
import re
import time
import urllib.parse
import xml.sax.saxutils

from django import http
from django.conf import settings
from django.core.cache import caches
from django.middleware import csrf
from django.contrib import auth
from django import urls
from rest_framework import views

from funkwhale_api.federation import utils as federation_utils

from . import preferences
from . import session
from . import throttling
from . import utils

EXCLUDED_PATHS = ["/api", "/federation", "/.well-known"]

logger = logging.getLogger(__name__)


def should_fallback_to_spa(path):
    if path == "/":
        return True
    return not any([path.startswith(m) for m in EXCLUDED_PATHS])


def serve_spa(request):
    html = get_spa_html(settings.FUNKWHALE_SPA_HTML_ROOT)
    head, tail = html.split("</head>", 1)
    if settings.FUNKWHALE_SPA_REWRITE_MANIFEST:
        new_url = (
            settings.FUNKWHALE_SPA_REWRITE_MANIFEST_URL
            or federation_utils.full_url(urls.reverse("api:v1:instance:spa-manifest"))
        )
        title = preferences.get("instance__name")
        if title:
            head = replace_title(head, title)
        head = replace_manifest_url(head, new_url)

    if not preferences.get("common__api_authentication_required"):
        try:
            request_tags = get_request_head_tags(request) or []
        except urls.exceptions.Resolver404:
            # we don't have any custom tags for this route
            request_tags = []
    else:
        # API is not open, we don't expose any custom data
        request_tags = []
    default_tags = get_default_head_tags(request.path)
    unique_attributes = ["name", "property"]

    final_tags = request_tags
    skip = []

    for t in final_tags:
        for attr in unique_attributes:
            if attr in t:
                skip.append(t[attr])
    for t in default_tags:
        existing = False
        for attr in unique_attributes:
            if t.get(attr) in skip:
                existing = True
                break
        if not existing:
            final_tags.append(t)

    # let's inject our meta tags in the HTML
    head += "\n" + "\n".join(render_tags(final_tags)) + "\n</head>"
    css = get_custom_css() or ""
    if css:
        # We add the style add the end of the body to ensure it has the highest
        # priority (since it will come after other stylesheets)
        body, tail = tail.split("</body>", 1)
        css = "<style>{}</style>".format(css)
        tail = body + "\n" + css + "\n</body>" + tail

    # set a csrf token so that visitor can login / query API if needed
    token = csrf.get_token(request)
    response = http.HttpResponse(head + tail)
    response.set_cookie("csrftoken", token, max_age=None)
    return response


MANIFEST_LINK_REGEX = re.compile(r"<link [^>]*rel=(?:'|\")?manifest(?:'|\")?[^>]*>")
TITLE_REGEX = re.compile(r"<title>.*</title>")


def replace_manifest_url(head, new_url):
    replacement = '<link rel=manifest href="{}">'.format(new_url)
    head = MANIFEST_LINK_REGEX.sub(replacement, head)
    return head


def replace_title(head, new_title):
    replacement = "<title>{}</title>".format(html.escape(new_title))
    head = TITLE_REGEX.sub(replacement, head)
    return head


def get_spa_html(spa_url):
    return get_spa_file(spa_url, "index.html")


def get_spa_file(spa_url, name):
    if spa_url.startswith("/"):
        # spa_url is an absolute path to index.html, on the local disk.
        # However, we may want to access manifest.json or other files as well, so we
        # strip the filename
        path = os.path.join(os.path.dirname(spa_url), name)
        # we try to open a local file
        with open(path, "rb") as f:
            return f.read().decode("utf-8")
    cache_key = "spa-file:{}:{}".format(spa_url, name)
    cached = caches["local"].get(cache_key)
    if cached:
        return cached

    response = session.get_session().get(utils.join_url(spa_url, name),)
    response.raise_for_status()
    content = response.text
    caches["local"].set(cache_key, content, settings.FUNKWHALE_SPA_HTML_CACHE_DURATION)
    return content


def get_default_head_tags(path):
    instance_name = preferences.get("instance__name")
    short_description = preferences.get("instance__short_description")
    app_name = settings.APP_NAME

    parts = [instance_name, app_name]

    return [
        {"tag": "meta", "property": "og:type", "content": "website"},
        {
            "tag": "meta",
            "property": "og:site_name",
            "content": " - ".join([p for p in parts if p]),
        },
        {"tag": "meta", "property": "og:description", "content": short_description},
        {
            "tag": "meta",
            "property": "og:image",
            "content": utils.join_url(settings.FUNKWHALE_URL, "/front/favicon.png"),
        },
        {
            "tag": "meta",
            "property": "og:url",
            "content": utils.join_url(settings.FUNKWHALE_URL, path),
        },
    ]


def render_tags(tags):
    """
    Given a dict like {'tag': 'meta', 'hello': 'world'}
    return a html ready tag like
    <meta hello="world" />
    """
    for tag in tags:

        yield "<{tag} {attrs} />".format(
            tag=tag.pop("tag"),
            attrs=" ".join(
                [
                    '{}="{}"'.format(a, html.escape(str(v)))
                    for a, v in sorted(tag.items())
                    if v
                ]
            ),
        )


def get_request_head_tags(request):
    accept_header = request.headers.get("Accept") or None
    redirect_to_ap = (
        False
        if not accept_header
        else not federation_utils.should_redirect_ap_to_html(accept_header)
    )
    match = urls.resolve(request.path, urlconf=settings.SPA_URLCONF)
    return match.func(
        request, *match.args, redirect_to_ap=redirect_to_ap, **match.kwargs
    )


def get_custom_css():
    css = preferences.get("ui__custom_css").strip()
    if not css:
        return

    return xml.sax.saxutils.escape(css)


class ApiRedirect(Exception):
    def __init__(self, url):
        self.url = url


def get_api_response(request, url):
    """
    Quite ugly but we have no choice. When Accept header is set to application/activity+json
    some clients expect to get a JSON payload (instead of the HTML we return). Since
    redirecting to the URL does not work (because it makes the signature verification fail),
    we grab the internal view corresponding to the URL, call it and return this as the
    response
    """
    path = urllib.parse.urlparse(url).path

    try:
        match = urls.resolve(path)
    except urls.exceptions.Resolver404:
        return http.HttpResponseNotFound()
    response = match.func(request, *match.args, **match.kwargs)
    if hasattr(response, "render"):
        response.render()
    return response


class SPAFallbackMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if response.status_code == 404 and should_fallback_to_spa(request.path):
            try:
                return serve_spa(request)
            except ApiRedirect as e:
                return get_api_response(request, e.url)

        return response


class DevHttpsMiddleware:
    """
    In development, it's sometimes difficult to have django use HTTPS
    when we have django behind nginx behind traefix.

    We thus use a simple setting (in dev ONLY) to control that.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.FORCE_HTTPS_URLS:
            setattr(request.__class__, "scheme", "https")
            setattr(
                request,
                "get_host",
                lambda: request.__class__.get_host(request).replace(":80", ":443"),
            )
        return self.get_response(request)


def monkey_patch_rest_initialize_request():
    """
    Rest framework use it's own APIRequest, meaning we can't easily
    access our throttling info in the middleware. So me monkey patch the
    `initialize_request` method from rest_framework to keep a link between both requests
    """
    original = views.APIView.initialize_request

    def replacement(self, request, *args, **kwargs):
        r = original(self, request, *args, **kwargs)
        setattr(request, "_api_request", r)
        return r

    setattr(views.APIView, "initialize_request", replacement)


monkey_patch_rest_initialize_request()


def monkey_patch_auth_get_user():
    """
    We need an actor on our users for many endpoints, so we monkey patch
    auth.get_user to create it if it's missing
    """
    original = auth.get_user

    def replacement(request):
        r = original(request)
        if not r.is_anonymous and not r.actor:
            r.create_actor()
        return r

    setattr(auth, "get_user", replacement)


monkey_patch_auth_get_user()


class ThrottleStatusMiddleware:
    """
    Include useful information regarding throttling in API responses to
    ensure clients can adapt.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
        except throttling.TooManyRequests:
            # manual throttling in non rest_framework view, we have to return
            # the proper response ourselves
            response = http.HttpResponse(status=429)
        request_to_check = request
        try:
            request_to_check = request._api_request
        except AttributeError:
            pass
        throttle_status = getattr(request_to_check, "_throttle_status", None)
        if throttle_status:
            response["X-RateLimit-Limit"] = str(throttle_status["num_requests"])
            response["X-RateLimit-Scope"] = str(throttle_status["scope"])
            response["X-RateLimit-Remaining"] = throttle_status["num_requests"] - len(
                throttle_status["history"]
            )
            response["X-RateLimit-Duration"] = str(throttle_status["duration"])
            if throttle_status["history"]:
                now = int(time.time())
                # At this point, the client can send additional requests
                oldtest_request = throttle_status["history"][-1]
                remaining = throttle_status["duration"] - (now - int(oldtest_request))
                response["Retry-After"] = str(remaining)
                # At this point, all Rate Limit is reset to 0
                latest_request = throttle_status["history"][0]
                remaining = throttle_status["duration"] - (now - int(latest_request))
                response["X-RateLimit-Reset"] = str(now + remaining)
                response["X-RateLimit-ResetSeconds"] = str(remaining)

        return response


class VerboseBadRequestsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 400:
            logger.warning("Bad request: %s", response.content)
        return response


class ProfilerMiddleware:
    """
    from https://github.com/omarish/django-cprofile-middleware/blob/master/django_cprofile_middleware/middleware.py
    Simple profile middleware to profile django views. To run it, add ?prof to
    the URL like this:
        http://localhost:8000/view/?prof
    Optionally pass the following to modify the output:
    ?sort => Sort the output by a given metric. Default is time.
        See
        http://docs.python.org/2/library/profile.html#pstats.Stats.sort_stats
        for all sort options.
    ?count => The number of rows to display. Default is 100.
    ?download => Download profile file suitable for visualization. For example
        in snakeviz or RunSnakeRun
    This is adapted from an example found here:
    http://www.slideshare.net/zeeg/django-con-high-performance-django-presentation.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if "prof" not in request.GET:
            return self.get_response(request)
        import profile
        import pstats

        profiler = profile.Profile()
        response = profiler.runcall(self.get_response, request)
        profiler.create_stats()
        if "prof-download" in request.GET:
            import marshal

            output = marshal.dumps(profiler.stats)
            response = http.HttpResponse(
                output, content_type="application/octet-stream"
            )
            response["Content-Disposition"] = "attachment; filename=view.prof"
            response["Content-Length"] = len(output)
        stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stream)

        stats.sort_stats(request.GET.get("prof-sort", "cumtime"))
        stats.print_stats(int(request.GET.get("count", 100)))

        response = http.HttpResponse("<pre>%s</pre>" % stream.getvalue())

        return response

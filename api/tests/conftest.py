import contextlib
import datetime
import io
import os
import PIL
import random
import shutil
import tempfile
import uuid

from faker.providers import internet as internet_provider
import factory
import pytest

from django.core.management import call_command
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache as django_cache, caches
from django.core.files import uploadedfile
from django.utils import timezone
from django.test import client
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models import QuerySet

from aioresponses import aioresponses
from dynamic_preferences.registries import global_preferences_registry
from rest_framework import fields as rest_fields
from rest_framework.test import APIClient, APIRequestFactory

from funkwhale_api.activity import record
from funkwhale_api.common import plugins
from funkwhale_api.federation import actors
from funkwhale_api.moderation import mrf


pytest_plugins = "aiohttp.pytest_plugin"


class FunkwhaleProvider(internet_provider.Provider):
    """
    Our own faker data generator, since built-in ones are sometimes
    not random enough
    """

    def federation_url(self, prefix=""):
        def path_generator():
            return "{}/{}".format(prefix, uuid.uuid4())

        domain = self.domain_name()
        protocol = "https"
        path = path_generator()
        return "{}://{}/{}".format(protocol, domain, path)


factory.Faker.add_provider(FunkwhaleProvider)


@pytest.fixture
def queryset_equal_queries():
    """
    Unitting querysets is hard because we have to compare queries
    by hand. Let's monkey patch querysets to do that for us.
    """

    def __eq__(self, other):
        if isinstance(other, QuerySet):
            return str(other.query) == str(self.query)
        else:
            return False

    setattr(QuerySet, "__eq__", __eq__)
    yield __eq__
    delattr(QuerySet, "__eq__")


@pytest.fixture
def queryset_equal_list():
    """
    Unitting querysets is hard because we usually simply wants to ensure
    a querysets contains the same objects as a list, let's monkey patch
    querysets to to that for us.
    """

    def __eq__(self, other):
        if isinstance(other, (list, tuple)):
            return list(self) == list(other)
        else:
            return False

    setattr(QuerySet, "__eq__", __eq__)
    yield __eq__
    delattr(QuerySet, "__eq__")


@pytest.fixture(scope="session", autouse=True)
def factories_autodiscover():
    from django.apps import apps
    from funkwhale_api import factories

    app_names = [app.name for app in apps.app_configs.values()]
    factories.registry.autodiscover(app_names)


@pytest.fixture(autouse=True)
def cache():
    """
    Returns a django Cache instance for cache-related operations
    """
    yield django_cache
    django_cache.clear()


@pytest.fixture(autouse=True)
def local_cache():
    yield caches["local"]
    caches["local"].clear()


@pytest.fixture
def factories(db):
    """
    Returns a dictionnary containing all registered factories with keys such as
    users.User or music.Track
    """
    from funkwhale_api import factories

    for v in factories.registry.values():
        try:
            v._meta.strategy = factory.CREATE_STRATEGY
        except AttributeError:
            # probably not a class based factory
            pass
    yield factories.registry


@pytest.fixture
def nodb_factories():
    """
    Returns a dictionnary containing all registered factories with a build strategy
    that does not require access to the database
    """
    from funkwhale_api import factories

    for v in factories.registry.values():
        try:
            v._meta.strategy = factory.BUILD_STRATEGY
        except AttributeError:
            # probably not a class based factory
            pass
    yield factories.registry


@pytest.fixture
def preferences(db, cache):
    """
    return a dynamic_preferences manager for global_preferences
    """
    manager = global_preferences_registry.manager()
    manager.all()
    yield manager


@pytest.fixture
def tmpdir():
    """
    Returns a temporary directory path where you can write things during your
    test
    """
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)


@pytest.fixture
def tmpfile():
    """
    Returns a temporary file where you can write things during your test
    """
    yield tempfile.NamedTemporaryFile()


@pytest.fixture
def logged_in_client(db, factories, client):
    """
    Returns a logged-in, non-API client with an authenticated ``User``
    stored in the ``user`` attribute
    """
    user = factories["users.User"]()
    assert client.login(username=user.username, password="test")
    setattr(client, "user", user)
    yield client
    delattr(client, "user")


@pytest.fixture
def anonymous_user():
    """Returns a AnonymousUser() instance"""
    return AnonymousUser()


@pytest.fixture
def api_client(client):
    """
    Return an API client without any authentication
    """
    return APIClient()


@pytest.fixture
def logged_in_api_client(db, factories, api_client):
    """
    Return a logged-in API client with an authenticated ``User``
    stored in the ``user`` attribute
    """
    user = factories["users.User"]()
    assert api_client.login(username=user.username, password="test")
    api_client.force_authenticate(user=user)
    setattr(api_client, "user", user)
    yield api_client
    delattr(api_client, "user")


@pytest.fixture
def superuser_api_client(db, factories, api_client):
    """
    Return a logged-in API client with an authenticated superuser
    stored in the ``user`` attribute
    """
    user = factories["users.SuperUser"]()
    assert api_client.login(username=user.username, password="test")
    setattr(api_client, "user", user)
    yield api_client
    delattr(api_client, "user")


@pytest.fixture
def superuser_client(db, factories, client):
    """
    Return a logged-in, non-API client with an authenticated ``User``
    stored in the ``user`` attribute
    """
    user = factories["users.SuperUser"]()
    assert client.login(username=user.username, password="test")
    setattr(client, "user", user)
    yield client
    delattr(client, "user")


@pytest.fixture
def api_request():
    """
    Returns a dummy API request object you can pass to API views
    """
    return APIRequestFactory()


@pytest.fixture
def fake_request():
    """
    Returns a dummy, non-API request object you can pass to regular views
    """
    return client.RequestFactory()


@pytest.fixture
def activity_registry():
    state = list(record.registry.items())
    yield record.registry
    record.registry.clear()
    for key, value in state:
        record.registry[key] = value


@pytest.fixture
def activity_muted(activity_registry, mocker):
    yield mocker.patch.object(record, "send")


@pytest.fixture(autouse=True)
def media_root(settings):
    """
    Sets settings.MEDIA_ROOT to a temporary path and returns this path
    """
    tmp_dir = tempfile.mkdtemp()
    settings.MEDIA_ROOT = tmp_dir
    yield settings.MEDIA_ROOT
    shutil.rmtree(tmp_dir)


@pytest.fixture(autouse=True)
def disabled_musicbrainz(mocker):
    # we ensure no music brainz requests gets out
    yield mocker.patch(
        "musicbrainzngs.musicbrainz._safe_read",
        side_effect=Exception("Disabled network calls"),
    )


@pytest.fixture(autouse=True)
def r_mock(requests_mock):
    """
    Returns a requests_mock.mock() object you can use to mock HTTP calls made
    using python-requests
    """
    yield requests_mock


@pytest.fixture
def authenticated_actor(factories, mocker):
    """
    Returns an authenticated ActivityPub actor
    """
    actor = factories["federation.Actor"]()
    mocker.patch(
        "funkwhale_api.federation.authentication.SignatureAuthentication.authenticate_actor",
        return_value=actor,
    )
    yield actor


@pytest.fixture
def to_api_date():
    def inner(value):
        if isinstance(value, datetime.datetime):
            f = rest_fields.DateTimeField()
            return f.to_representation(value)
        if isinstance(value, datetime.date):
            f = rest_fields.DateField()
            return f.to_representation(value)
        raise ValueError("Invalid value: {}".format(value))

    return inner


@pytest.fixture()
def now(mocker):
    now = timezone.now()
    mocker.patch("django.utils.timezone.now", return_value=now)
    return now


@pytest.fixture()
def avatar():
    i = PIL.Image.new("RGBA", (400, 400), random.choice(["red", "blue", "yellow"]))
    f = io.BytesIO()
    i.save(f, "png")
    f.name = "avatar.png"
    f.seek(0)
    yield f
    f.close()


@pytest.fixture()
def audio_file():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music")
    path = os.path.join(data_dir, "test.ogg")
    assert os.path.exists(path)
    with open(path, "rb") as f:
        yield f


@pytest.fixture()
def uploaded_audio_file(audio_file):
    yield uploadedfile.SimpleUploadedFile(
        name=audio_file.name, content=audio_file.read()
    )


@pytest.fixture()
def temp_signal(mocker):
    """
    Connect a temporary handler to a given signal. This is helpful to validate
    a signal is dispatched properly, without mocking.
    """

    @contextlib.contextmanager
    def connect(signal):
        stub = mocker.stub()
        signal.connect(stub)
        try:
            yield stub
        finally:
            signal.disconnect(stub)

    return connect


@pytest.fixture()
def stdout():
    yield io.StringIO()


@pytest.fixture
def spa_html(r_mock, settings):
    settings.FUNKWHALE_SPA_HTML_ROOT = "http://noop/"
    yield r_mock.get(
        settings.FUNKWHALE_SPA_HTML_ROOT + "index.html", text="<head></head>"
    )


@pytest.fixture
def no_api_auth(preferences):
    preferences["common__api_authentication_required"] = False


@pytest.fixture()
def migrator(transactional_db):
    yield MigrationExecutor(connection)
    call_command("migrate", interactive=False)


@pytest.fixture(autouse=True)
def rsa_small_key(settings):
    # smaller size for faster generation, since it's CPU hungry
    settings.RSA_KEY_SIZE = 512


@pytest.fixture(autouse=True)
def a_responses():
    with aioresponses() as m:
        yield m


@pytest.fixture
def service_actor(db):
    return actors.get_service_actor()


@pytest.fixture
def mrf_inbox_registry(mocker):
    registry = mrf.Registry()
    mocker.patch("funkwhale_api.moderation.mrf.inbox", registry)
    return registry


@pytest.fixture
def mrf_outbox_registry(mocker):
    registry = mrf.Registry()
    mocker.patch("funkwhale_api.moderation.mrf.outbox", registry)
    return registry


@pytest.fixture
def plugins_registry(mocker):
    mocker.patch.dict(plugins.registry, {})
    mocker.patch.object(
        plugins.Plugin, "_path_from_module", return_value="/tmp/dummypath"
    )
    return plugins.registry

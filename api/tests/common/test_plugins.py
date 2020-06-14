import os

import pytest

from django.urls import resolvers

from funkwhale_api.common import plugins


class P(plugins.Plugin):
    name = "test_plugin"
    path = os.path.abspath(__file__)


@pytest.fixture
def plugin(settings):
    yield P(app_name="test_plugin", app_module="tests.common.test_plugins.main.P")


@pytest.fixture(autouse=True)
def clear_patterns():
    plugins.urlpatterns.clear()
    resolvers._get_cached_resolver.cache_clear()
    yield
    resolvers._get_cached_resolver.cache_clear()


def test_can_register_view(plugin, mocker, settings):
    view = mocker.Mock()
    plugin.register_api_view("hello", name="hello")(view)
    expected = "/plugins/test-plugin/hello"
    assert plugins.reverse("plugins-test_plugin-hello") == expected
    assert plugins.resolve(expected).func == view


def test_plugin_view_middleware_not_matching(api_client, plugin, mocker, settings):
    view = mocker.Mock()
    get_response = mocker.Mock()
    middleware = plugins.PluginViewMiddleware(get_response)
    plugin.register_api_view("hello", name="hello")(view)
    request = mocker.Mock(path=plugins.reverse("plugins-test_plugin-hello"))
    response = middleware(request)
    assert response == get_response.return_value
    view.assert_not_called()


def test_plugin_view_middleware_matching(api_client, plugin, mocker, settings):
    view = mocker.Mock()
    get_response = mocker.Mock(return_value=mocker.Mock(status_code=404))
    middleware = plugins.PluginViewMiddleware(get_response)
    plugin.register_api_view("hello/<slug:slug>", name="hello")(view)
    request = mocker.Mock(
        path=plugins.reverse("plugins-test_plugin-hello", kwargs={"slug": "world"})
    )
    response = middleware(request)
    assert response == view.return_value
    view.assert_called_once_with(request, slug="world")

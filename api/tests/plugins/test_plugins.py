import os
import sys

import pytest

from django.urls import reverse

from rest_framework import serializers

from funkwhale_api.common import models
from config import plugins


@pytest.fixture(autouse=True)
def _plugins():
    plugins._filters.clear()
    plugins._hooks.clear()
    plugins._plugins.clear()
    yield
    plugins._filters.clear()
    plugins._hooks.clear()
    plugins._plugins.clear()


def test_register_filter():
    filters = {}
    plugin_config = plugins.get_plugin_config("test", {})

    def handler(value, conf):
        return value + 1

    plugins.register_filter("test_filter", plugin_config, filters)(handler)
    plugins.register_filter("test_filter", plugin_config, filters)(handler)

    assert len(filters["test_filter"]) == 2
    assert plugins.trigger_filter("test_filter", 1, confs={}, registry=filters) == 3


def test_register_hook(mocker):
    hooks = {}
    plugin_config = plugins.get_plugin_config("test", {})
    mock = mocker.Mock()

    def handler(conf):
        mock()

    plugins.register_hook("test_hook", plugin_config, hooks)(handler)
    plugins.register_hook("test_hook", plugin_config, hooks)(handler)
    plugins.trigger_hook("test_hook", confs={}, registry=hooks)
    assert mock.call_count == 2
    assert len(hooks["test_hook"]) == 2


def test_get_plugin_conf():
    _plugins = {}
    plugin_config = plugins.get_plugin_config(
        "test", description="Hello", registry=_plugins
    )
    assert plugin_config["name"] == "test"
    assert plugin_config["description"] == "Hello"
    assert plugin_config["user"] is False
    assert _plugins == {
        "test": plugin_config,
    }


def test_set_plugin_conf_validates():
    _plugins = {}
    plugins.get_plugin_config(
        "test", registry=_plugins, conf=[{"name": "foo", "type": "boolean"}]
    )

    with pytest.raises(serializers.ValidationError):
        plugins.set_conf("test", {"foo": "noop"}, registry=_plugins)


def test_set_plugin_conf_valid():
    _plugins = {}
    plugins.get_plugin_config(
        "test", registry=_plugins, conf=[{"name": "foo", "type": "boolean"}]
    )
    plugins.set_conf("test", {"foo": True}, registry=_plugins)

    conf = models.PluginConfiguration.objects.latest("id")
    assert conf.code == "test"
    assert conf.conf == {"foo": True}
    assert conf.user is None


def test_set_plugin_conf_valid_user(factories):
    user = factories["users.User"]()
    _plugins = {}
    plugins.get_plugin_config(
        "test", registry=_plugins, conf=[{"name": "foo", "type": "boolean"}]
    )

    plugins.set_conf("test", {"foo": True}, user=user, registry=_plugins)

    conf = models.PluginConfiguration.objects.latest("id")
    assert conf.code == "test"
    assert conf.conf == {"foo": True}
    assert conf.user == user


def test_get_confs(factories):
    plugins.get_plugin_config("test1")
    plugins.get_plugin_config("test2")
    factories["common.PluginConfiguration"](code="test1", conf={"hello": "world"})
    factories["common.PluginConfiguration"](code="test2", conf={"foo": "bar"})

    assert plugins.get_confs() == {
        "test1": {"conf": {"hello": "world"}, "enabled": False},
        "test2": {"conf": {"foo": "bar"}, "enabled": False},
    }


def test_get_confs_user(factories):
    plugins.get_plugin_config("test1")
    plugins.get_plugin_config("test2")
    plugins.get_plugin_config("test3")
    user1 = factories["users.User"]()
    user2 = factories["users.User"]()
    factories["common.PluginConfiguration"](code="test1", conf={"hello": "world"})
    factories["common.PluginConfiguration"](code="test2", conf={"foo": "bar"})
    factories["common.PluginConfiguration"](
        code="test3", conf={"user": True}, user=user1
    )
    factories["common.PluginConfiguration"](
        code="test4", conf={"user": False}, user=user2
    )

    assert plugins.get_confs(user=user1) == {
        "test1": {"conf": {"hello": "world"}, "enabled": False},
        "test2": {"conf": {"foo": "bar"}, "enabled": False},
        "test3": {"conf": {"user": True}, "enabled": False},
    }


def test_filter_is_called_with_plugin_conf(mocker, factories):
    plugins.get_plugin_config("test1",)
    plugins.get_plugin_config("test2",)
    factories["common.PluginConfiguration"](code="test1", enabled=True)
    factories["common.PluginConfiguration"](
        code="test2", conf={"foo": "baz"}, enabled=True
    )
    confs = plugins.get_confs()
    filters = {}
    plugin_config1 = plugins.get_plugin_config("test1", {})
    plugin_config2 = plugins.get_plugin_config("test2", {})

    handler1 = mocker.Mock()
    handler2 = mocker.Mock()

    plugins.register_filter("test_filter", plugin_config1, filters)(handler1)
    plugins.register_filter("test_filter", plugin_config2, filters)(handler2)

    plugins.trigger_filter("test_filter", 1, confs=confs, registry=filters)

    handler1.assert_called_once_with(1, conf=confs["test1"])
    handler2.assert_called_once_with(handler1.return_value, conf=confs["test2"])


def test_get_serializer_from_conf_template():
    template = [
        {
            "name": "enabled",
            "type": "boolean",
            "default": True,
            "label": "Enable plugin",
        },
        {
            "name": "api_url",
            "type": "url",
            "label": "URL of the scrobbler API",
            "validator": lambda self, v: v + "/test",
        },
    ]

    serializer_class = plugins.get_serializer_from_conf_template(template)

    data = {
        "enabled": True,
        "api_url": "http://hello.world",
    }

    serializer = serializer_class(data=data)
    assert serializer.is_valid(raise_exception=True) is True
    assert serializer.validated_data == {
        "enabled": True,
        "api_url": "http://hello.world/test",
    }


def test_serialize_plugin():
    plugin = plugins.get_plugin_config(
        name="test_plugin",
        description="Hello world",
        conf=[{"name": "foo", "type": "boolean"}],
    )

    expected = {
        "name": "test_plugin",
        "enabled": False,
        "description": "Hello world",
        "conf": [{"name": "foo", "type": "boolean"}],
        "user": False,
        "source": False,
        "label": "test_plugin",
        "values": None,
    }

    assert plugins.serialize_plugin(plugin, plugins.get_confs()) == expected


def test_serialize_plugin_user(factories):
    user = factories["users.User"]()
    plugin = plugins.get_plugin_config(
        name="test_plugin",
        description="Hello world",
        conf=[{"name": "foo", "type": "boolean"}],
        user=True,
    )

    expected = {
        "name": "test_plugin",
        "enabled": False,
        "description": "Hello world",
        "conf": [{"name": "foo", "type": "boolean"}],
        "user": True,
        "source": False,
        "label": "test_plugin",
        "values": None,
    }

    assert plugins.serialize_plugin(plugin, plugins.get_confs(user)) == expected


def test_serialize_plugin_user_enabled(factories):
    user = factories["users.User"]()
    plugin = plugins.get_plugin_config(
        name="test_plugin",
        description="Hello world",
        conf=[{"name": "foo", "type": "boolean"}],
        user=True,
    )

    factories["common.PluginConfiguration"](
        code="test_plugin", user=user, enabled=True, conf={"foo": "bar"}
    )
    expected = {
        "name": "test_plugin",
        "enabled": True,
        "description": "Hello world",
        "conf": [{"name": "foo", "type": "boolean"}],
        "user": True,
        "source": False,
        "label": "test_plugin",
        "values": {"foo": "bar"},
    }

    assert plugins.serialize_plugin(plugin, plugins.get_confs(user)) == expected


def test_can_list_user_plugins(logged_in_api_client):
    plugin = plugins.get_plugin_config(
        name="test_plugin",
        description="Hello world",
        conf=[{"name": "foo", "type": "boolean"}],
        user=True,
    )
    plugins.get_plugin_config(name="test_plugin2", user=False)
    url = reverse("api:v1:plugins-list")
    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert response.data == [
        plugins.serialize_plugin(plugin, plugins.get_confs(logged_in_api_client.user))
    ]


def test_can_retrieve_user_plugin(logged_in_api_client):
    plugin = plugins.get_plugin_config(
        name="test_plugin",
        description="Hello world",
        conf=[{"name": "foo", "type": "boolean"}],
        user=True,
    )
    plugins.get_plugin_config(name="test_plugin2", user=False)
    url = reverse("api:v1:plugins-detail", kwargs={"pk": "test_plugin"})
    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert response.data == plugins.serialize_plugin(
        plugin, plugins.get_confs(logged_in_api_client.user)
    )


def test_can_update_user_plugin(logged_in_api_client):
    plugin = plugins.get_plugin_config(
        name="test_plugin",
        description="Hello world",
        conf=[{"name": "foo", "type": "boolean"}],
        user=True,
    )
    plugins.get_plugin_config(name="test_plugin2", user=False)
    url = reverse("api:v1:plugins-detail", kwargs={"pk": "test_plugin"})
    response = logged_in_api_client.post(url, {"foo": True})
    assert response.status_code == 200
    assert logged_in_api_client.user.plugins.latest("id").conf == {"foo": True}
    assert response.data == plugins.serialize_plugin(
        plugin, plugins.get_confs(logged_in_api_client.user)
    )


def test_can_destroy_user_plugin(logged_in_api_client):
    plugins.get_plugin_config(
        name="test_plugin",
        description="Hello world",
        conf=[{"name": "foo", "type": "boolean"}],
        user=True,
    )
    plugins.set_conf("test_plugin", {"foo": True}, user=logged_in_api_client.user)
    plugins.get_plugin_config(name="test_plugin2", user=False)
    url = reverse("api:v1:plugins-detail", kwargs={"pk": "test_plugin"})
    response = logged_in_api_client.delete(url, {"enabled": True})
    assert response.status_code == 204

    with pytest.raises(models.PluginConfiguration.DoesNotExist):
        assert logged_in_api_client.user.plugins.latest("id")


def test_can_enable_user_plugin(logged_in_api_client):
    plugins.get_plugin_config(
        name="test_plugin",
        description="Hello world",
        conf=[{"name": "foo", "type": "boolean"}],
        user=True,
    )
    plugins.set_conf("test_plugin", {"foo": True}, user=logged_in_api_client.user)
    url = reverse("api:v1:plugins-enable", kwargs={"pk": "test_plugin"})
    response = logged_in_api_client.post(url)
    assert response.status_code == 200

    assert logged_in_api_client.user.plugins.latest("id").enabled is True


def test_can_disable_user_plugin(logged_in_api_client):
    plugins.get_plugin_config(
        name="test_plugin",
        description="Hello world",
        conf=[{"name": "foo", "type": "boolean"}],
        user=True,
    )
    plugins.set_conf("test_plugin", {"foo": True}, user=logged_in_api_client.user)
    url = reverse("api:v1:plugins-disable", kwargs={"pk": "test_plugin"})
    response = logged_in_api_client.post(url)
    assert response.status_code == 200

    assert logged_in_api_client.user.plugins.latest("id").enabled is False


def test_can_install_dependencies(mocker):
    dependencies = ["depa==12", "depb"]
    check_call = mocker.patch("subprocess.check_call")
    expected = [
        os.path.join(os.path.dirname(sys.executable), "pip"),
        "install",
    ] + dependencies
    plugins.install_dependencies(dependencies)
    check_call.assert_called_once_with(expected)


def test_set_plugin_source_conf_invalid(factories):
    user = factories["users.User"]()
    _plugins = {}
    plugins.get_plugin_config(
        "test",
        source=True,
        registry=_plugins,
        conf=[{"name": "foo", "type": "boolean"}],
    )
    with pytest.raises(serializers.ValidationError):
        plugins.set_conf("test", {"foo": True}, user=user, registry=_plugins)


def test_set_plugin_source_conf_valid(factories):
    library = factories["music.Library"](actor__local=True)
    _plugins = {}
    plugins.get_plugin_config(
        "test",
        source=True,
        registry=_plugins,
        conf=[{"name": "foo", "type": "boolean"}],
    )
    plugins.set_conf(
        "test",
        {"foo": True, "library": library.uuid},
        user=library.actor.user,
        registry=_plugins,
    )
    conf = models.PluginConfiguration.objects.latest("id")
    assert conf.code == "test"
    assert conf.conf == {"foo": True, "library": str(library.uuid)}
    assert conf.user == library.actor.user


def test_can_trigger_scan(logged_in_api_client, mocker, factories):
    library = factories["music.Library"](actor=logged_in_api_client.user.create_actor())
    plugin = plugins.get_plugin_config(
        name="test_plugin", description="Hello world", conf=[], source=True,
    )
    handler = mocker.Mock()
    plugins.register_hook(plugins.SCAN, plugin)(handler)
    plugins.set_conf(
        "test_plugin", {"library": library.uuid}, user=logged_in_api_client.user
    )
    url = reverse("api:v1:plugins-scan", kwargs={"pk": "test_plugin"})
    plugins.enable_conf("test_plugin", True, logged_in_api_client.user)
    response = logged_in_api_client.post(url)
    assert response.status_code == 200

    handler.assert_called_once_with(
        library=library, conf={"library": str(library.uuid)}
    )

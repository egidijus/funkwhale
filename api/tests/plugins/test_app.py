import pytest

from funkwhale_api import plugins
from funkwhale_api.plugins import models


def test_plugin_ready_calls_load(mocker, plugin):
    load = mocker.spy(plugin, "load")
    plugin.ready()

    load.assert_called_once_with()


def test_get_plugin_not_found(mocker):
    get_app_config = mocker.patch(
        "django.apps.apps.get_app_config", side_effect=LookupError
    )

    with pytest.raises(plugins.PluginNotFound):
        plugins.get_plugin("noop")

    get_app_config.assert_called_once_with("noop")


def test_get_plugin_not_plugin(mocker):
    get_app_config = mocker.spy(plugins.apps.apps, "get_app_config")

    with pytest.raises(plugins.PluginNotFound):
        plugins.get_plugin("music")

    get_app_config.assert_called_once_with("music")


def test_get_plugin_valid(mocker):
    get_app_config = mocker.patch("django.apps.apps.get_app_config")
    get_app_config.return_value = mocker.Mock(_is_funkwhale_plugin=True)
    assert plugins.get_plugin("test") is get_app_config.return_value

    get_app_config.assert_called_once_with("test")


def test_plugin_attributes(plugin):
    assert isinstance(plugin.hooks, plugins.HookRegistry)
    assert isinstance(plugin.settings, plugins.SettingRegistry)
    assert isinstance(plugin.user_settings, plugins.SettingRegistry)


def test_plugin_hook_connect(plugin):
    @plugin.hooks.connect("hook_name")
    def handler(**kwargs):
        pass

    assert plugin.hooks["hook_name"] == handler


def test_plugin_user_settings_register(plugin):
    @plugin.user_settings.register
    class TestSetting(plugins.config.StringSetting):
        section = plugins.config.SettingSection("test")
        name = "test_setting"
        default = ""

    assert plugin.user_settings["test__test_setting"] == TestSetting


def test_plugin_settings_register(plugin):
    @plugin.settings.register
    class TestSetting(plugins.config.StringSetting):
        section = plugins.config.SettingSection("test")
        name = "test_setting"
        default = ""

    assert plugin.settings["test__test_setting"] == TestSetting


def test_get_all_plugins(mocker):
    pl1 = mocker.Mock(_is_funkwhale_plugin=True)
    pl2 = mocker.Mock(_is_funkwhale_plugin=True)
    app = mocker.Mock(_is_funkwhale_plugin=False)
    mocker.patch("django.apps.apps.get_app_configs", return_value=[pl1, pl2, app])
    all_plugins = plugins.get_all_plugins()

    assert all_plugins == [pl1, pl2]


def test_generate_plugin_conf(factories, plugin_class):
    plugin1 = plugin_class("test1", "test1")
    plugin2 = plugin_class("test2", "test2")
    plugin3 = plugin_class("test3", "test3")
    plugin4 = plugin_class("test4", "test4")

    user = factories["users.User"]()
    # this one is enabled
    plugin1_db_conf = factories["plugins.Plugin"](name=plugin1.name)
    # this one is enabled, with additional user-level configuration (see below)
    plugin2_db_conf = factories["plugins.Plugin"](name=plugin2.name)
    # this one is disabled at the plugin level, so it shouldn't appear in the final conf
    plugin3_db_conf = factories["plugins.Plugin"](name=plugin3.name, is_enabled=False)
    # this one is enabled, but disabled at user level (see below)
    plugin4_db_conf = factories["plugins.Plugin"](name=plugin4.name)
    # this one doesn't match any registered app
    factories["plugins.Plugin"](name="noop")

    # a user-level configuration but with a different user, so irrelevant
    factories["plugins.UserPlugin"](plugin=plugin1_db_conf)
    # a user-level configuration but the plugin is disabled
    factories["plugins.UserPlugin"](user=user, plugin=plugin3_db_conf)
    # a user-level configuration, plugin is enabled, should be reflected in the final conf
    plugin2_user_db_conf = factories["plugins.UserPlugin"](
        user=user, plugin=plugin2_db_conf
    )
    # a user-level configuration, plugin is enabled but disabled by user, should be reflected in the final conf
    factories["plugins.UserPlugin"](user=user, plugin=plugin4_db_conf, is_enabled=False)

    expected = [
        {"obj": plugin1, "settings": plugin1_db_conf.config, "user": None},
        {
            "obj": plugin2,
            "settings": plugin2_db_conf.config,
            "user": {"id": user.pk, "settings": plugin2_user_db_conf.config},
        },
        {"obj": plugin4, "settings": plugin4_db_conf.config, "user": None},
    ]

    conf = plugins.generate_plugin_conf([plugin1, plugin2, plugin3, plugin4], user=user)
    assert conf == expected


def test_generate_plugin_conf_anonymous_user(factories, plugin_class):
    plugin1 = plugin_class("test1", "test1")
    plugin2 = plugin_class("test2", "test2")
    plugin3 = plugin_class("test3", "test3")
    plugin4 = plugin_class("test4", "test4")

    user = factories["users.User"]()
    # this one is enabled
    plugin1_db_conf = factories["plugins.Plugin"](name=plugin1.name)
    # this one is enabled, with additional user-level configuration (see below)
    plugin2_db_conf = factories["plugins.Plugin"](name=plugin2.name)
    # this one is disabled at the plugin level, so it shouldn't appear in the final conf
    plugin3_db_conf = factories["plugins.Plugin"](name=plugin3.name, is_enabled=False)
    # this one is enabled, but disabled at user level (see below)
    plugin4_db_conf = factories["plugins.Plugin"](name=plugin4.name)
    # this one doesn't match any registered app
    factories["plugins.Plugin"](name="noop")

    # a user-level configuration but with a different user, so irrelevant
    factories["plugins.UserPlugin"](plugin=plugin1_db_conf)
    # a user-level configuration but the plugin is disabled
    factories["plugins.UserPlugin"](user=user, plugin=plugin3_db_conf)
    expected = [
        {"obj": plugin1, "settings": plugin1_db_conf.config, "user": None},
        {"obj": plugin2, "settings": plugin2_db_conf.config, "user": None},
        {"obj": plugin4, "settings": plugin4_db_conf.config, "user": None},
    ]

    conf = plugins.generate_plugin_conf([plugin1, plugin2, plugin3, plugin4], user=None)
    assert conf == expected


def test_attach_plugin_conf(mocker):
    request = mocker.Mock()
    generate_plugin_conf = mocker.patch.object(plugins, "generate_plugin_conf")
    get_all_plugins = mocker.patch.object(plugins, "get_all_plugins")
    user = mocker.Mock()

    plugins.attach_plugin_conf(request, user=user)

    generate_plugin_conf.assert_called_once_with(
        plugins=get_all_plugins.return_value, user=user
    )
    assert request.plugin_conf == generate_plugin_conf.return_value


def test_attach_plugin_noop_if_plugins_disabled(mocker, preferences):
    preferences["plugins__enabled"] = False
    request = mocker.Mock()

    plugins.attach_plugin_conf(request, user=None)

    assert request.plugin_conf is None

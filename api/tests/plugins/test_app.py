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


def test_generate_plugins_conf(factories, plugin_class):
    plugin1 = plugin_class("test1", "test1")
    plugin2 = plugin_class("test3", "test3")
    plugin3 = plugin_class("test4", "test4")

    # this one is enabled
    plugin1_db_conf = factories["plugins.Plugin"](name=plugin1.name)
    # this one is disabled at the plugin level, so it shouldn't appear in the final conf
    factories["plugins.Plugin"](name=plugin3.name, is_enabled=False)
    # this one doesn't match any registered app
    factories["plugins.Plugin"](name="noop")

    expected = [{"obj": plugin1, "settings": plugin1_db_conf.config, "user": None}]

    conf = plugins.generate_plugins_conf([plugin1, plugin2, plugin3])
    assert conf == expected


def test_update_plugins_conf_with_user_settings(factories, plugin_class):
    plugin1 = plugin_class("test1", "test1")
    plugin2 = plugin_class("test2", "test2")
    plugin3 = plugin_class("test3", "test3")

    user = factories["users.User"]()

    # user has enabled this plugin and has custom settings
    plugin1_user_conf = factories["plugins.UserPlugin"](
        plugin__name=plugin1.name, user=user
    )
    # plugin is disabled by user
    plugin2_user_conf = factories["plugins.UserPlugin"](
        plugin__name=plugin2.name, user=user, is_enabled=False
    )
    # Plugin is enabled by another user
    plugin3_user_conf = factories["plugins.UserPlugin"](plugin__name=plugin3.name)

    expected = [
        {
            "obj": plugin1,
            "settings": plugin1_user_conf.plugin.config,
            "user": {"id": user.pk, "settings": plugin1_user_conf.config},
        },
        {"obj": plugin2, "settings": plugin2_user_conf.plugin.config, "user": None},
        {"obj": plugin3, "settings": plugin3_user_conf.plugin.config, "user": None},
    ]

    conf = plugins.generate_plugins_conf([plugin1, plugin2, plugin3])
    assert plugins.update_plugins_conf_with_user_settings(conf, user=user) == expected


def test_update_plugins_conf_with_user_settings_anonymous(factories, plugin_class):
    plugin1 = plugin_class("test1", "test1")
    plugin2 = plugin_class("test2", "test2")
    plugin3 = plugin_class("test3", "test3")

    plugin1_db_conf = factories["plugins.Plugin"](name=plugin1.name)
    plugin2_db_conf = factories["plugins.Plugin"](name=plugin2.name)
    plugin3_db_conf = factories["plugins.Plugin"](name=plugin3.name)

    expected = [
        {"obj": plugin1, "settings": plugin1_db_conf.config, "user": None},
        {"obj": plugin2, "settings": plugin2_db_conf.config, "user": None},
        {"obj": plugin3, "settings": plugin3_db_conf.config, "user": None},
    ]

    conf = plugins.generate_plugins_conf([plugin1, plugin2, plugin3])
    assert plugins.update_plugins_conf_with_user_settings(conf, user=None) == expected


def test_attach_plugins_conf(mocker):
    request = mocker.Mock()
    generate_plugins_conf = mocker.patch.object(plugins, "generate_plugins_conf")
    get_all_plugins = mocker.patch.object(plugins, "get_all_plugins")

    plugins.attach_plugins_conf(request)

    generate_plugins_conf.assert_called_once_with(plugins=get_all_plugins.return_value)
    assert request.plugins_conf == generate_plugins_conf.return_value


def test_attach_plugin_noop_if_plugins_disabled(mocker, preferences):
    preferences["plugins__enabled"] = False
    request = mocker.Mock()

    plugins.attach_plugins_conf(request)

    assert request.plugins_conf is None

from funkwhale_api.common import plugins

# setup code to populate plugins registry
# plugin-to-user -> enable and configure
# plugin preferences


def test_plugin_register(plugins_registry):
    class TestPlugin(plugins.Plugin):
        name = "scrobbler"
        verbose_name = "Audio Scrobbler"

    inst = TestPlugin(app_name="scrobbler", app_module="")
    plugins_registry.register(inst)

    assert inst.plugins_registry == plugins_registry
    assert inst.is_initialized is False
    assert plugins_registry["scrobbler"] == inst
    assert inst.config == {}


def test_plugin_get_config(plugins_registry):
    class TestPlugin(plugins.Plugin):
        name = "scrobbler"
        verbose_name = "Audio Scrobbler"

    plugin = TestPlugin(app_name="", app_module="")
    assert plugin.get_config({"hello": "world"}) == {"hello": "world"}


def test_plugin_set_config(plugins_registry):
    class TestPlugin(plugins.Plugin):
        name = "scrobbler"
        verbose_name = "Audio Scrobbler"

    plugin = TestPlugin(app_name="", app_module="")
    plugin.set_config({"hello": "world"})
    assert plugin.config == {"hello": "world"}


def test_plugin_initialize(plugins_registry):
    class TestPlugin(plugins.Plugin):
        name = "scrobbler"
        verbose_name = "Audio Scrobbler"

    plugin = TestPlugin(app_name="", app_module="")
    assert plugin.initialize() is None


def test_action(mocker, plugins_registry):
    class TestPlugin(plugins.Plugin):
        name = "scrobbler"
        verbose_name = "Audio Scrobbler"

    inst = TestPlugin(app_name="scrobbler", app_module="")
    plugins_registry.register(inst)

    stub = mocker.stub()

    # nothing hooked, so stub is not called
    plugins_registry.dispatch_action("hello", user="test", arg1="value1", arg2="value2")
    stub.assert_not_called()

    # now we hook the stub on the action
    inst.register_action("hello", stub)
    assert inst.hooked_actions == {"hello": stub}
    plugins_registry.dispatch_action("hello", user="test", arg1="value1", arg2="value2")

    stub.assert_called_once_with(plugin=inst, user="test", arg1="value1", arg2="value2")


def test_plugins_init(plugins_registry, mocker):
    class TestPlugin1(plugins.Plugin):
        name = "scrobbler"
        verbose_name = "Audio Scrobbler"

    class TestPlugin2(plugins.Plugin):
        name = "webhooks"
        verbose_name = "Webhooks"

    plugin1 = TestPlugin1(app_name="scrobbler", app_module="")
    plugin2 = TestPlugin2(app_name="webhooks", app_module="")

    mocks = {}
    for plugin in [plugin1, plugin2]:
        d = {
            "get_config": mocker.patch.object(plugin, "get_config"),
            "set_config": mocker.patch.object(plugin, "set_config"),
            "initialize": mocker.patch.object(plugin, "initialize"),
        }
        mocks[plugin.name] = d

    autodiscover = mocker.patch.object(plugins_registry, "autodiscover")
    plugins.init(plugins_registry, [plugin1, plugin2])

    autodiscover.assert_called_once_with([plugin1.name, plugin2.name])

    for mock_conf in mocks.values():
        mock_conf["get_config"].assert_called_once_with({})
        mock_conf["set_config"].assert_called_once_with(
            mock_conf["get_config"].return_value
        )
        mock_conf["initialize"].assert_called_once_with()

    assert plugin1.is_initialized is True
    assert plugin2.is_initialized is True

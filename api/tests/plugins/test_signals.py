import pytest

from funkwhale_api import plugins


def test_hooks_register():
    hook = plugins.Hook("history.listenings.created", providing_args=["listening"])
    plugins.hooks.register(hook)

    assert plugins.hooks["history.listenings.created"] == hook


def test_hooks_dispatch(mocker, plugin_class):
    plugin1 = plugin_class("test1", "test1")
    plugin2 = plugin_class("test2", "test2")
    hook = plugins.Hook("history.listenings.created", providing_args=["listening"])
    plugins.hooks.register(hook)

    handler1 = mocker.stub()
    handler2 = mocker.stub()
    plugin1.hooks.connect("history.listenings.created")(handler1)
    plugin2.hooks.connect("history.listenings.created")(handler2)

    plugins_conf = [
        {"obj": plugin1, "user": {"hello": "world"}, "settings": {"foo": "bar"}},
        {"obj": plugin2},
    ]
    plugins.hooks.dispatch(
        "history.listenings.created", listening="test", plugins_conf=plugins_conf
    )
    handler1.assert_called_once_with(listening="test", plugin_conf=plugins_conf[0])
    handler2.assert_called_once_with(listening="test", plugin_conf=plugins_conf[1])


def test_hooks_dispatch_exception_fail_loudly_false(mocker, plugin_class, settings):
    settings.PLUGINS_FAIL_LOUDLY = False
    plugin1 = plugin_class("test1", "test1")
    plugin2 = plugin_class("test2", "test2")
    hook = plugins.Hook("history.listenings.created", providing_args=["listening"])
    plugins.hooks.register(hook)

    handler1 = mocker.stub()
    handler2 = mocker.Mock(side_effect=Exception("hello"))
    plugin1.hooks.connect("history.listenings.created")(handler1)
    plugin2.hooks.connect("history.listenings.created")(handler2)
    plugins_conf = [
        {"obj": plugin1, "user": {"hello": "world"}, "settings": {"foo": "bar"}},
        {"obj": plugin2},
    ]
    plugins.hooks.dispatch(
        "history.listenings.created", listening="test", plugins_conf=plugins_conf
    )
    handler1.assert_called_once_with(listening="test", plugin_conf=plugins_conf[0])
    handler2.assert_called_once_with(listening="test", plugin_conf=plugins_conf[1])


def test_hooks_dispatch_exception_fail_loudly_true(mocker, plugin_class, settings):
    settings.PLUGINS_FAIL_LOUDLY = True
    plugin1 = plugin_class("test1", "test1")
    plugin2 = plugin_class("test2", "test2")
    hook = plugins.Hook("history.listenings.created", providing_args=["listening"])
    plugins.hooks.register(hook)

    handler1 = mocker.Mock(side_effect=Exception("hello"))
    handler2 = mocker.stub()
    plugin1.hooks.connect("history.listenings.created")(handler1)
    plugin2.hooks.connect("history.listenings.created")(handler2)
    plugins_conf = [
        {"obj": plugin1, "user": {"hello": "world"}, "settings": {"foo": "bar"}},
        {"obj": plugin2},
    ]
    with pytest.raises(Exception, match=r".*hello.*"):
        plugins.hooks.dispatch(
            "history.listenings.created", listening="test", plugins_conf=plugins_conf
        )
    handler1.assert_called_once_with(listening="test", plugin_conf=plugins_conf[0])
    handler2.assert_not_called()

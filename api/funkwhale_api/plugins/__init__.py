import persisting_theory

import django.dispatch
from django import apps

import logging

from . import config

logger = logging.getLogger(__name__)


class Plugin(apps.AppConfig):
    _is_funkwhale_plugin = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hooks = HookRegistry()
        self.settings = SettingRegistry()
        self.user_settings = SettingRegistry()

    def ready(self):
        super().ready()
        logging.info("Loading plugin %s…", self.label)
        self.load()
        logging.info("Plugin %s loaded", self.label)

    def load(self):
        pass


class FuncRegistry(persisting_theory.Registry):
    def connect(self, hook_name):
        def inner(handler):
            self[hook_name] = handler
            return handler

        return inner


class HookRegistry(FuncRegistry):
    pass


class SettingRegistry(persisting_theory.Registry):
    def prepare_name(self, data, name):
        return data().identifier()


class PluginException(Exception):
    pass


class PluginNotFound(PluginException):
    pass


class Skip(PluginException):
    pass


class PluginSignal(object):
    def __init__(self, name, providing_args=[]):
        self.name = name
        self.providing_args = providing_args


class Hook(PluginSignal):
    pass


class SignalsRegistry(persisting_theory.Registry):
    def prepare_name(self, data, name):
        return data.name

    def dispatch(self, hook_name, plugins_conf, **kwargs):
        """
        Call all handlers connected to hook_name in turn.
        """
        if hook_name not in self:
            raise LookupError(hook_name)
        logger.debug("[Plugin:hook:%s] Dispatching hook", hook_name)
        matching_hooks = []
        for row in plugins_conf:
            try:
                matching_hooks.append((row, row["obj"].hooks[hook_name]))
            except KeyError:
                continue
        if matching_hooks:
            logger.debug(
                "[Plugin:hook:%s] %s handlers found", hook_name, len(matching_hooks)
            )
        else:
            logger.debug("[Plugin:hook:%s] No handler founds", hook_name)
            return

        for row, handler in matching_hooks:
            logger.debug(
                "[Plugin:hook:%s] Calling handler %s from plugin %s",
                hook_name,
                handler,
                row["obj"].name,
            )
            try:
                handler(plugin_conf=row, **kwargs)
            except Skip:
                logger.debug("[Plugin:hook:%s] handler skipped", hook_name)
            except Exception:
                logger.exception(
                    "[Plugin:hook:%s] unknown exception with handler %s",
                    hook_name,
                    handler,
                )
            else:
                logger.debug("[Plugin:hook:%s] handler %s called successfully", handler)

        logger.debug("[Plugin:hook:%s] Done", hook_name)


hooks = SignalsRegistry()


def get_plugin(name):
    try:
        plugin = apps.apps.get_app_config(name)
    except LookupError:
        raise PluginNotFound(name)

    if not getattr(plugin, "_is_funkwhale_plugin", False):
        raise PluginNotFound(name)

    return plugin


def get_all_plugins():
    return [
        app
        for app in apps.apps.get_app_configs()
        if getattr(app, "_is_funkwhale_plugin", False)
    ]


def generate_plugins_conf(plugins, user=None):
    from . import models

    plugins_conf = []
    qs = models.Plugin.objects.filter(is_enabled=True).values("name", "config")
    by_plugin_name = {obj["name"]: obj["config"] for obj in qs}
    for plugin in plugins:
        if plugin.name not in by_plugin_name:
            continue
        conf = {
            "obj": plugin,
            "user": None,
            "settings": by_plugin_name[plugin.name] or {},
        }
        plugins_conf.append(conf)

    if plugins_conf and user and user.is_authenticated:
        qs = models.UserPlugin.objects.filter(
            user=user, plugin__is_enabled=True, is_enabled=True
        ).values("plugin__name", "config")
        by_plugin_name = {obj["plugin__name"]: obj["config"] for obj in qs}
        for row in plugins_conf:
            if row["obj"].name in by_plugin_name:
                row["user"] = {
                    "id": user.pk,
                    "settings": by_plugin_name[row["obj"].name],
                }
    return plugins_conf


def attach_plugins_conf(obj, user):
    from funkwhale_api.common import preferences

    plugins_enabled = preferences.get("plugins__enabled")
    if plugins_enabled:
        conf = generate_plugins_conf(plugins=get_all_plugins(), user=user)
    else:
        conf = None
    setattr(obj, "plugins_conf", conf)

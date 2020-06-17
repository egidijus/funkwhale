from django.apps import AppConfig

from pluggy import PluginManager, HookimplMarker, HookspecMarker

plugins_manager = PluginManager("funkwhale")
plugin_hook = HookimplMarker("funkwhale")
plugin_spec = HookspecMarker("funkwhale")


class ConfigError(ValueError):
    pass


class Plugin(AppConfig):
    conf = {}
    path = "noop"

    def get_conf(self):
        return {"enabled": self.plugin_settings.enabled}

    def plugin_settings(self):
        """
        Return plugin specific settings from django.conf.settings
        """
        from django.conf import settings

        d = {}
        for key in dir(settings):
            k = key.lower()
            if not k.startswith("plugin_{}_".format(self.name.lower())):
                continue

            value = getattr(settings, key)
            s_key = k.replace("plugin_{}_".format(self.name.lower()), "")
            d[s_key] = value
            return clean(d, self.conf, self.name)


def clean(d, conf, plugin_name):
    cleaned = {}
    for key, c in conf.items():
        if key in d:
            try:
                cleaned[key] = c["validator"](d[key])
            except (ValueError, TypeError, AttributeError):
                raise ConfigError(
                    "Invalid value {} for setting {} in plugin {}".format(
                        d[key], key, plugin_name
                    )
                )

        else:
            cleaned[key] = c["default"]

    return cleaned


class HookSpec:
    @plugin_spec
    def database_engine(self):
        """
        Customize the database engine with a new class
        """

    @plugin_spec
    def register_apps(self):
        """
        Register additional apps in INSTALLED_APPS.

        :rvalue: list"""

    @plugin_spec
    def middlewares_before(self):
        """
        Register additional middlewares at the outer level.

        :rvalue: list"""

    @plugin_spec
    def middlewares_after(self):
        """
        Register additional middlewares at the inner level.

        :rvalue: list"""

    def urls(self):
        """
        Register additional urls.

        :rvalue: list"""


plugins_manager.add_hookspecs(HookSpec())


def register(plugin_class):
    return plugins_manager.register(plugin_class("noop", "noop"))


def trigger_hook(name, *args, **kwargs):
    handler = getattr(plugins_manager.hook, name)
    return handler(*args, **kwargs)


@register
class DefaultPlugin(Plugin):
    @plugin_hook
    def database_engine(self):
        return "django.db.backends.postgresql"

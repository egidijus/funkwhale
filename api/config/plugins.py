from django import urls
from pluggy import PluginManager, HookimplMarker, HookspecMarker

plugins_manager = PluginManager("funkwhale")
hook = HookimplMarker("funkwhale")
hookspec = HookspecMarker("funkwhale")


class PluginViewMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings

        response = self.get_response(request)
        if response.status_code == 404 and request.path.startswith("/plugins/"):
            match = urls.resolve(request.path, urlconf=settings.PLUGINS_URLCONF)
            response = match.func(request, *match.args, **match.kwargs)
        return response


class ConfigError(ValueError):
    pass


class Plugin:
    conf = {}

    def get_conf(self):
        return {"enabled": self.plugin_settings.enabled}

    def register_api_view(self, path, name=None):
        def register(view):
            return urls.path(
                "plugins/{}/{}".format(self.name.replace("_", "-"), path),
                view,
                name="plugins-{}-{}".format(self.name, name),
            )

        return register

    def plugin_settings(self):
        """
        Return plugin specific settings from django.conf.settings
        """
        import ipdb

        ipdb.set_trace()
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


def reverse(name, **kwargs):
    from django.conf import settings

    return urls.reverse(name, settings.PLUGINS_URLCONF, **kwargs)


def resolve(name, **kwargs):
    from django.conf import settings

    return urls.resolve(name, settings.PLUGINS_URLCONF, **kwargs)


# def install_plugin(name_or_path):

#     subprocess.check_call([sys.executable, "-m", "pip", "install", package])
#     sub


class HookSpec:
    @hookspec
    def register_apps(self):
        """
        Register additional apps in INSTALLED_APPS.

        :rvalue: list"""

    @hookspec
    def middlewares_before(self):
        """
        Register additional middlewares at the outer level.

        :rvalue: list"""

    @hookspec
    def middlewares_after(self):
        """
        Register additional middlewares at the inner level.

        :rvalue: list"""

    @hookspec
    def urls(self):
        """
        Register additional urls.

        :rvalue: list"""


plugins_manager.add_hookspecs(HookSpec())

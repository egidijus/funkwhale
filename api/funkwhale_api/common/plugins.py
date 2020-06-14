from django.apps import AppConfig
from django import urls
from django.conf import settings


urlpatterns = []


class PluginViewMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 404 and request.path.startswith("/plugins/"):
            match = urls.resolve(request.path, urlconf=settings.PLUGINS_URLCONF)
            response = match.func(request, *match.args, **match.kwargs)
        return response


class Plugin(AppConfig):
    def ready(self):
        from . import main  # noqa

        return super().ready()

    def register_api_view(self, path, name=None):
        def register(view):
            urlpatterns.append(
                urls.path(
                    "plugins/{}/{}".format(self.name.replace("_", "-"), path),
                    view,
                    name="plugins-{}-{}".format(self.name, name),
                )
            ),

        return register


def reverse(name, **kwargs):
    return urls.reverse(name, settings.PLUGINS_URLCONF, **kwargs)


def resolve(name, **kwargs):
    return urls.resolve(name, settings.PLUGINS_URLCONF, **kwargs)

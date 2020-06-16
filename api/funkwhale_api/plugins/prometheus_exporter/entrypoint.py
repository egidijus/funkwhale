import json
from django import http
from django import urls

from config import plugins


class Plugin(plugins.Plugin):
    name = "prometheus_exporter"

    @plugins.hook
    def register_apps(self):
        return "django_prometheus"

    @plugins.hook
    def middlewares_before(self):
        return [
            "django_prometheus.middleware.PrometheusBeforeMiddleware",
        ]

    @plugins.hook
    def middlewares_after(self):
        return [
            "django_prometheus.middleware.PrometheusAfterMiddleware",
        ]

    @plugins.hook
    def urls(self):
        return [urls.url(r"^plugins/prometheus/exporter/?$", prometheus)]


plugins.plugins_manager.register(Plugin())


def prometheus(request):
    stats = {"foo": "bar"}
    return http.HttpResponse(json.dumps(stats))

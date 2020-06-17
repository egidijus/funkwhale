from django.conf.urls import url, include

from config import plugins


@plugins.register
class Plugin(plugins.Plugin):
    name = "prometheus_exporter"

    @plugins.plugin_hook
    def database_engine(self):
        return "django_prometheus.db.backends.postgresql"

    @plugins.plugin_hook
    def register_apps(self):
        return "django_prometheus"

    @plugins.plugin_hook
    def middlewares_before(self):
        return [
            "django_prometheus.middleware.PrometheusBeforeMiddleware",
        ]

    @plugins.plugin_hook
    def middlewares_after(self):
        return [
            "django_prometheus.middleware.PrometheusAfterMiddleware",
        ]

    @plugins.plugin_hook
    def urls(self):
        return [url(r"^prometheus/", include("django_prometheus.urls"))]

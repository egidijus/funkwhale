from django.apps import AppConfig, apps

from . import mutations
from . import utils


class CommonConfig(AppConfig):
    name = "funkwhale_api.common"

    def ready(self):
        super().ready()

        app_names = [app.name for app in apps.app_configs.values()]
        mutations.registry.autodiscover(app_names)
        utils.monkey_patch_request_build_absolute_uri()

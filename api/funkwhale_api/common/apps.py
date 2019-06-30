"""
Ideal API:

# myplugin/apps.py

from funkwhale_api import plugins

class Plugin(plugins.Plugin):
    name = 'scrobbler'
    config_options = [
        {
            'id': 'user_agent',
            'verbose_name': 'User agent string',
            'help_text': 'The user agent string used by this plugin for external HTTP request',
            'default': None,
        },
        {
            'id': 'timeout',
            'type': 'int',
            'verbose_name': 'Timeout (in seconds)'
            'help_text': 'Max timeout for HTTP calls',
            'default': 10,
        },
    ]

    def get_user_options(self):
        from . import options
        return [
            options.ListenBrainz,
            options.LastFm,
        ]


# myplugin/hooks.py

from .apps import Plugin


@Plugin.register_action('history.listening_created')
def scrobble(plugin, user, listening, **kwargs):
    user_options = plugin.get_options(user)

    if len(options) == 0:
        return

    for option in user_options:
        if option.id == 'listenbrainz':
            broadcast_to_listenbrainz()



"""
from django.apps import AppConfig, apps

from . import mutations
from . import plugins


class CommonConfig(AppConfig):
    name = "funkwhale_api.common"

    def ready(self):
        super().ready()

        app_names = [app.name for app in apps.app_configs.values()]
        mutations.registry.autodiscover(app_names)

        plugins.init(
            plugins.registry,
            [
                app
                for app in apps.app_configs.values()
                if getattr(app, "_is_funkwhale_plugin", False) is True
            ],
        )

from funkwhale_api import plugins


class Plugin(plugins.Plugin):
    name = "fw_scrobbler"
    help = "A simple plugin that enables scrobbling to ListenBrainz and Last.fm"
    version = "0.1"

    def load(self):
        from . import config
        from . import hooks

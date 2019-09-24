from funkwhale_api import plugins

plugin = plugins.get_plugin("fw_scrobbler")
service = plugins.config.SettingSection("service", "Scrobbling Service")


@plugin.user_settings.register
class URL(plugins.config.StringSetting):
    section = service
    name = "url"
    default = ""
    verbose_name = "URL of the scrobbler service"
    help = (
        "Suggested choices:\n\n",
        "- LastFM (default if left empty): http://post.audioscrobbler.com\n",
        "- ListenBrainz: http://proxy.listenbrainz.org/",
        "- ListenBrainz: http://proxy.listenbrainz.org/",
        "- Libre.fm: http://turtle.libre.fm/",
    )


@plugin.user_settings.register
class Username(plugins.config.StringSetting):
    section = service
    name = "username"
    default = ""
    verbose_name = "Your scrobbler username"


@plugin.user_settings.register
class Password(plugins.config.PasswordSetting):
    section = service
    name = "password"
    default = ""
    verbose_name = "Your scrobbler password"

from funkwhale_api import plugins

from . import scrobbler

plugin = plugins.get_plugin("fw_scrobbler")

# https://listenbrainz.org/lastfm-proxy
DEFAULT_SCROBBLER_URL = "http://post.audioscrobbler.com"


@plugin.hooks.connect("history.listening.created")
def forward_to_scrobblers(listening, plugin_conf, **kwargs):
    if plugin_conf["user"] is None:
        raise plugins.Skip()

    username = plugin_conf["user"]["settings"].get("service__username")
    password = plugin_conf["user"]["settings"].get("service__password")
    url = plugin_conf["user"]["settings"].get("service__url", DEFAULT_SCROBBLER_URL)
    if username and password:
        plugin.logger.info("Forwarding scrobbler to %s", url)
        session = plugin.get_requests_session()
        session_key, scrobble_url = scrobbler.handshake_v1(
            session=session, url=url, username=username, password=password
        )
        scrobbler.submit_scrobble_v1(
            session=session,
            track=listening.track,
            scrobble_time=listening.creation_date,
            session_key=session_key,
            scrobble_url=scrobble_url,
        )
    else:
        plugin.logger.debug("No scrobbler configuration for user, skipping")

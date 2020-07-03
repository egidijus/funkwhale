from config import plugins

from .funkwhale_startup import PLUGIN

from . import scrobbler

# https://listenbrainz.org/lastfm-proxy
DEFAULT_SCROBBLER_URL = "http://post.audioscrobbler.com"


@plugins.register_hook(plugins.LISTENING_CREATED, PLUGIN)
def forward_to_scrobblers(listening, conf, **kwargs):
    if not conf:
        raise plugins.Skip()

    username = conf.get("username")
    password = conf.get("password")
    url = conf.get("url", DEFAULT_SCROBBLER_URL) or DEFAULT_SCROBBLER_URL
    if username and password:
        PLUGIN["logger"].info("Forwarding scrobbler to %s", url)
        session = plugins.get_session()
        session_key, now_playing_url, scrobble_url = scrobbler.handshake_v1(
            session=session, url=url, username=username, password=password
        )
        scrobbler.submit_now_playing_v1(
            session=session,
            track=listening.track,
            session_key=session_key,
            now_playing_url=now_playing_url,
        )
        scrobbler.submit_scrobble_v1(
            session=session,
            track=listening.track,
            scrobble_time=listening.creation_date,
            session_key=session_key,
            scrobble_url=scrobble_url,
        )
    else:
        PLUGIN["logger"].debug("No scrobbler configuration for user, skipping")

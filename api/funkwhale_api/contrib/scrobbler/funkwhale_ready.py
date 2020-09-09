import hashlib

from config import plugins
from .funkwhale_startup import PLUGIN

from . import scrobbler

# https://listenbrainz.org/lastfm-proxy
DEFAULT_SCROBBLER_URL = "http://post.audioscrobbler.com"
LASTFM_SCROBBLER_URL = "https://ws.audioscrobbler.com/2.0/"


@plugins.register_hook(plugins.LISTENING_CREATED, PLUGIN)
def forward_to_scrobblers(listening, conf, **kwargs):
    if not conf:
        raise plugins.Skip()

    username = conf.get("username")
    password = conf.get("password")
    url = conf.get("url", DEFAULT_SCROBBLER_URL) or DEFAULT_SCROBBLER_URL
    if username and password:
        session = plugins.get_session()
        if (
            PLUGIN["settings"]["lastfm_api_key"]
            and PLUGIN["settings"]["lastfm_api_secret"]
            and url == DEFAULT_SCROBBLER_URL
        ):
            hashed_auth = hashlib.md5(
                (username + " " + password).encode("utf-8")
            ).hexdigest()
            cache_key = "lastfm:sessionkey:{}".format(
                ":".join([str(listening.user.pk), hashed_auth])
            )
            PLUGIN["logger"].info("Forwarding scrobble to %s", LASTFM_SCROBBLER_URL)
            session_key = PLUGIN["cache"].get(cache_key)
            if not session_key:
                PLUGIN["logger"].debug("Authenticating…")
                session_key = scrobbler.handshake_v2(
                    username=username,
                    password=password,
                    scrobble_url=LASTFM_SCROBBLER_URL,
                    session=session,
                    api_key=PLUGIN["settings"]["lastfm_api_key"],
                    api_secret=PLUGIN["settings"]["lastfm_api_secret"],
                )
                PLUGIN["cache"].set(cache_key, session_key)
            scrobbler.submit_scrobble_v2(
                session=session,
                track=listening.track,
                scrobble_time=listening.creation_date,
                session_key=session_key,
                scrobble_url=LASTFM_SCROBBLER_URL,
                api_key=PLUGIN["settings"]["lastfm_api_key"],
                api_secret=PLUGIN["settings"]["lastfm_api_secret"],
            )

        else:
            PLUGIN["logger"].info("Forwarding scrobble to %s", url)
            session_key, now_playing_url, scrobble_url = scrobbler.handshake_v1(
                session=session, url=url, username=username, password=password
            )
            scrobbler.submit_scrobble_v1(
                session=session,
                track=listening.track,
                scrobble_time=listening.creation_date,
                session_key=session_key,
                scrobble_url=scrobble_url,
            )
        PLUGIN["logger"].info("Scrobble sent!")
    else:
        PLUGIN["logger"].debug("No scrobbler configuration for user, skipping")

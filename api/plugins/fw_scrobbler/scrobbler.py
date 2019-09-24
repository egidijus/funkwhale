import hashlib
import time

import time

from funkwhale_api import plugins

from . import scrobbler

# https://github.com/jlieth/legacy-scrobbler
plugin = plugins.get_plugin("fw_scrobbler")


class ScrobblerException(Exception):
    pass


def handshake_v1(session, url, username, password):
    timestamp = str(int(time.time())).encode("utf-8")
    password_hash = hashlib.md5(password.encode("utf-8")).hexdigest()
    auth = hashlib.md5(password_hash.encode("utf-8") + timestamp).hexdigest()
    params = {
        "hs": "true",
        "p": "1.2",
        "c": plugin.name,
        "v": plugin.version,
        "u": username,
        "t": timestamp,
        "a": auth,
    }

    session = plugin.get_requests_session()
    plugin.logger.debug(
        "Performing scrobbler handshake for username %s at %s", username, url
    )
    handshake_response = session.get(url, params=params)
    # process response
    result = handshake_response.text.split("\n")
    if len(result) >= 4 and result[0] == "OK":
        session_key = result[1]
        nowplaying_url = result[2]
        scrobble_url = result[3]
    elif result[0] == "BANNED":
        raise ScrobblerException("BANNED")
    elif result[0] == "BADAUTH":
        raise ScrobblerException("BADAUTH")
    elif result[0] == "BADTIME":
        raise ScrobblerException("BADTIME")
    else:
        raise ScrobblerException(handshake_response.text)

    plugin.logger.debug("Handshake successful, scrobble url: %s", scrobble_url)
    return session_key, nowplaying_url, scrobble_url


def submit_scrobble_v1(session, scrobble_time, track, session_key, scrobble_url):
    payload = get_scrobble_payload(track, scrobble_time)
    plugin.logger.debug("Sending scrobble with payload %s", payload)
    payload["s"] = session_key
    response = session.post(scrobble_url, payload)
    response.raise_for_status()
    if response.text.startswith("OK"):
        return
    elif response.text.startswith("BADSESSION"):
        raise ScrobblerException("Remote server says the session is invalid")
    else:
        raise ScrobblerException(response.text)

    plugin.logger.debug("Scrobble successfull!")


def submit_now_playing_v1(session, track, session_key, now_playing_url):
    payload = get_scrobble_payload(track, date=None, suffix="")
    plugin.logger.debug("Sending now playing with payload %s", payload)
    payload["s"] = session_key
    response = session.post(now_playing_url, payload)
    response.raise_for_status()
    if response.text.startswith("OK"):
        return
    elif response.text.startswith("BADSESSION"):
        raise ScrobblerException("Remote server says the session is invalid")
    else:
        raise ScrobblerException(response.text)

    plugin.logger.debug("Now playing successfull!")


def get_scrobble_payload(track, date, suffix="[0]"):
    """
    Documentation available at https://web.archive.org/web/20190531021725/https://www.last.fm/api/submissions
    """
    upload = track.uploads.filter(duration__gte=0).first()
    data = {
        "a{}".format(suffix): track.artist.name,
        "t{}".format(suffix): track.title,
        "l{}".format(suffix): upload.duration if upload else 0,
        "b{}".format(suffix): track.album.title or "",
        "n{}".format(suffix): track.position or "",
        "m{}".format(suffix): str(track.mbid) or "",
        "o{}".format(suffix): "P",  # Source: P = chosen by user
    }
    if date:
        data["i{}".format(suffix)] = int(date.timestamp())
    return data

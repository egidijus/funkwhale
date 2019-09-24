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
        # nowplaying_url = result[2]
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
    return session_key, scrobble_url


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


def get_scrobble_payload(track, scrobble_time):
    upload = track.uploads.filter(duration__gte=0).first()
    return {
        "a[0]": track.artist.name,
        "t[0]": track.title,
        "i[0]": int(scrobble_time.timestamp()),
        "l[0]": upload.duration if upload else 0,
        "b[0]": track.album.title or "",
        "n[0]": track.position or "",
        "m[0]": str(track.mbid) or "",
    }

import hashlib
import time


# https://github.com/jlieth/legacy-scrobbler
from .funkwhale_startup import PLUGIN


class ScrobblerException(Exception):
    pass


def handshake_v1(session, url, username, password):
    timestamp = str(int(time.time())).encode("utf-8")
    password_hash = hashlib.md5(password.encode("utf-8")).hexdigest()
    auth = hashlib.md5(password_hash.encode("utf-8") + timestamp).hexdigest()
    params = {
        "hs": "true",
        "p": "1.2",
        "c": PLUGIN["name"],
        "v": PLUGIN["version"],
        "u": username,
        "t": timestamp,
        "a": auth,
    }

    PLUGIN["logger"].debug(
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

    PLUGIN["logger"].debug("Handshake successful, scrobble url: %s", scrobble_url)
    return session_key, nowplaying_url, scrobble_url


def submit_scrobble_v1(session, scrobble_time, track, session_key, scrobble_url):
    payload = get_scrobble_payload(track, scrobble_time)
    PLUGIN["logger"].debug("Sending scrobble with payload %s", payload)
    payload["s"] = session_key
    response = session.post(scrobble_url, payload)
    response.raise_for_status()
    if response.text.startswith("OK"):
        return
    elif response.text.startswith("BADSESSION"):
        raise ScrobblerException("Remote server says the session is invalid")
    else:
        raise ScrobblerException(response.text)

    PLUGIN["logger"].debug("Scrobble successfull!")


def submit_now_playing_v1(session, track, session_key, now_playing_url):
    payload = get_scrobble_payload(track, date=None, suffix="")
    PLUGIN["logger"].debug("Sending now playing with payload %s", payload)
    payload["s"] = session_key
    response = session.post(now_playing_url, payload)
    response.raise_for_status()
    if response.text.startswith("OK"):
        return
    elif response.text.startswith("BADSESSION"):
        raise ScrobblerException("Remote server says the session is invalid")
    else:
        raise ScrobblerException(response.text)

    PLUGIN["logger"].debug("Now playing successfull!")


def get_scrobble_payload(track, date, suffix="[0]"):
    """
    Documentation available at https://web.archive.org/web/20190531021725/https://www.last.fm/api/submissions
    """
    upload = track.uploads.filter(duration__gte=0).first()
    data = {
        "a{}".format(suffix): track.artist.name,
        "t{}".format(suffix): track.title,
        "l{}".format(suffix): upload.duration if upload else 0,
        "b{}".format(suffix): (track.album.title if track.album else "") or "",
        "n{}".format(suffix): track.position or "",
        "m{}".format(suffix): str(track.mbid) or "",
        "o{}".format(suffix): "P",  # Source: P = chosen by user
    }
    if date:
        data["i{}".format(suffix)] = int(date.timestamp())
    return data


def get_scrobble2_payload(track, date, suffix="[0]"):
    """
    Documentation available at https://web.archive.org/web/20190531021725/https://www.last.fm/api/submissions
    """
    upload = track.uploads.filter(duration__gte=0).first()
    data = {
        "artist": track.artist.name,
        "track": track.title,
        "chosenByUser": 1,
    }
    if upload:
        data["duration"] = upload.duration
    if track.album:
        data["album"] = track.album.title
    if track.position:
        data["trackNumber"] = track.position
    if track.mbid:
        data["mbid"] = str(track.mbid)
    if date:
        offset = upload.duration / 2 if upload.duration else 0
        data["timestamp"] = int(int(date.timestamp()) - offset)
    return data


def handshake_v2(username, password, session, api_key, api_secret, scrobble_url):
    params = {
        "method": "auth.getMobileSession",
        "username": username,
        "password": password,
        "api_key": api_key,
    }
    params["api_sig"] = hash_request(params, api_secret)
    response = session.post(scrobble_url, params)
    if 'status="ok"' not in response.text:
        raise ScrobblerException(response.text)

    session_key = response.text.split("<key>")[1].split("</key>")[0]
    return session_key


def submit_scrobble_v2(
    session, track, scrobble_time, session_key, scrobble_url, api_key, api_secret,
):
    params = {
        "method": "track.scrobble",
        "api_key": api_key,
        "sk": session_key,
    }
    scrobble = get_scrobble2_payload(track, scrobble_time)
    PLUGIN["logger"].debug("Scrobble payload: %s", scrobble)
    params.update(scrobble)
    params["api_sig"] = hash_request(params, api_secret)
    response = session.post(scrobble_url, params)
    if 'status="ok"' not in response.text:
        raise ScrobblerException(response.text)


def hash_request(data, secret_key):
    string = ""
    items = data.keys()
    items = sorted(items)
    for i in items:
        string += str(i)
        string += str(data[i])
    string += secret_key
    string_to_hash = string.encode("utf8")
    return hashlib.md5(string_to_hash).hexdigest()

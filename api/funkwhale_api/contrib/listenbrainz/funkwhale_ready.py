from config import plugins
from .funkwhale_startup import PLUGIN
from .client import ListenBrainzClient, Track


@plugins.register_hook(plugins.LISTENING_CREATED, PLUGIN)
def submit_listen(listening, conf, **kwargs):
    user_token = conf["user_token"]
    if not user_token:
        return

    logger = PLUGIN["logger"]
    logger.info("Submitting listen to ListenBrainz")
    client = ListenBrainzClient(user_token=user_token, logger=logger)
    track = get_track(listening.track)
    client.listen(int(listening.creation_date.timestamp()), track)


def get_track(track):
    artist = track.artist.name
    title = track.title
    album = None
    additional_info = {
        "listening_from": "Funkwhale",
        "tracknumber": track.position,
        "discnumber": track.disc_number,
    }

    if track.mbid:
        additional_info["recording_mbid"] = str(track.mbid)

    if track.album:
        if track.album.title:
            album = track.album.title
        if track.album.mbid:
            additional_info["release_mbid"] = str(track.album.mbid)

    if track.artist.mbid:
        additional_info["artist_mbids"] = [str(track.artist.mbid)]

    return Track(artist, title, album, additional_info)

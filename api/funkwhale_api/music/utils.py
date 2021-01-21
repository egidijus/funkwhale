import os
import pathlib
import mimetypes

import magic
import mutagen
import pydub

from django.conf import settings
from django.core.cache import cache
from django.db.models import F

from funkwhale_api.common import throttling
from funkwhale_api.common.search import get_fts_query  # noqa
from funkwhale_api.common.search import get_query  # noqa
from funkwhale_api.common.search import normalize_query  # noqa


def guess_mimetype(f):
    b = min(1000000, f.size)
    t = magic.from_buffer(f.read(b), mime=True)
    if not t.startswith("audio/"):
        t = guess_mimetype_from_name(f.name)

    return t


def guess_mimetype_from_name(name):
    # failure, we try guessing by extension
    mt, _ = mimetypes.guess_type(name)
    if mt:
        t = mt
    else:
        t = EXTENSION_TO_MIMETYPE.get(name.split(".")[-1])
    return t


def compute_status(jobs):
    statuses = jobs.order_by().values_list("status", flat=True).distinct()
    errored = any([status == "errored" for status in statuses])
    if errored:
        return "errored"
    pending = any([status == "pending" for status in statuses])
    if pending:
        return "pending"
    return "finished"


AUDIO_EXTENSIONS_AND_MIMETYPE = [
    # keep the most correct mimetype for each extension at the bottom
    ("mp3", "audio/mp3"),
    ("mp3", "audio/mpeg3"),
    ("mp3", "audio/x-mp3"),
    ("mp3", "audio/mpeg"),
    ("ogg", "video/ogg"),
    ("ogg", "audio/ogg"),
    ("opus", "audio/opus"),
    ("aac", "audio/x-m4a"),
    ("m4a", "audio/x-m4a"),
    ("flac", "audio/x-flac"),
    ("flac", "audio/flac"),
    ("aif", "audio/aiff"),
    ("aif", "audio/x-aiff"),
    ("aiff", "audio/aiff"),
    ("aiff", "audio/x-aiff"),
]

EXTENSION_TO_MIMETYPE = {ext: mt for ext, mt in AUDIO_EXTENSIONS_AND_MIMETYPE}
MIMETYPE_TO_EXTENSION = {mt: ext for ext, mt in AUDIO_EXTENSIONS_AND_MIMETYPE}

SUPPORTED_EXTENSIONS = list(
    sorted(set([ext for ext, _ in AUDIO_EXTENSIONS_AND_MIMETYPE]))
)


def get_ext_from_type(mimetype):
    return MIMETYPE_TO_EXTENSION.get(mimetype)


def get_type_from_ext(extension):
    if extension.startswith("."):
        # we remove leading dot
        extension = extension[1:]
    return EXTENSION_TO_MIMETYPE.get(extension)


def get_audio_file_data(f):
    data = mutagen.File(f)
    if not data:
        return
    d = {}
    d["bitrate"] = getattr(data.info, "bitrate", 0)
    d["length"] = data.info.length

    return d


def get_actor_from_request(request):
    actor = None
    if hasattr(request, "actor"):
        actor = request.actor
    elif request.user.is_authenticated:
        actor = request.user.actor

    return actor


def transcode_file(input, output, input_format=None, output_format="mp3", **kwargs):
    with input.open("rb"):
        audio = pydub.AudioSegment.from_file(input, format=input_format)
    return transcode_audio(audio, output, output_format, **kwargs)


def transcode_audio(audio, output, output_format, **kwargs):
    with output.open("wb"):
        return audio.export(output, format=output_format, **kwargs)


def increment_downloads_count(upload, user, wsgi_request):
    ident = throttling.get_ident(user=user, request=wsgi_request)
    cache_key = "downloads_count:upload-{}:{}-{}".format(
        upload.pk, ident["type"], ident["id"]
    )

    value = cache.get(cache_key)
    if value:
        # download already tracked
        return

    upload.downloads_count = F("downloads_count") + 1
    upload.track.downloads_count = F("downloads_count") + 1

    upload.save(update_fields=["downloads_count"])
    upload.track.save(update_fields=["downloads_count"])

    duration = max(upload.duration or 0, settings.MIN_DELAY_BETWEEN_DOWNLOADS_COUNT)

    cache.set(cache_key, 1, duration)


def browse_dir(root, path):
    if ".." in path:
        raise ValueError("Relative browsing is not allowed")

    root = pathlib.Path(root)
    real_path = root / path

    dirs = []
    files = []
    for el in sorted(os.listdir(real_path)):
        if os.path.isdir(real_path / el):
            dirs.append({"name": el, "dir": True})
        else:
            files.append({"name": el, "dir": False})

    return dirs + files

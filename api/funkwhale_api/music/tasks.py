import collections
import datetime
import logging
import os

from django.utils import timezone
from django.db import transaction
from django.db.models import F, Q
from django.dispatch import receiver

from musicbrainzngs import ResponseError
from requests.exceptions import RequestException

from funkwhale_api import musicbrainz
from funkwhale_api.common import channels, preferences
from funkwhale_api.common import utils as common_utils
from funkwhale_api.federation import routes
from funkwhale_api.federation import library as lb
from funkwhale_api.federation import utils as federation_utils
from funkwhale_api.tags import models as tags_models
from funkwhale_api.tags import tasks as tags_tasks
from funkwhale_api.taskapp import celery

from . import licenses
from . import models
from . import metadata
from . import signals

logger = logging.getLogger(__name__)


def populate_album_cover(album, source=None, replace=False):
    if album.attachment_cover and not replace:
        return
    if source and source.startswith("file://"):
        # let's look for a cover in the same directory
        path = os.path.dirname(source.replace("file://", "", 1))
        logger.info("[Album %s] scanning covers from %s", album.pk, path)
        cover = get_cover_from_fs(path)
        return common_utils.attach_file(album, "attachment_cover", cover)
    if album.mbid:
        logger.info(
            "[Album %s] Fetching cover from musicbrainz release %s",
            album.pk,
            str(album.mbid),
        )
        try:
            image_data = musicbrainz.api.images.get_front(str(album.mbid))
        except ResponseError as exc:
            logger.warning(
                "[Album %s] cannot fetch cover from musicbrainz: %s", album.pk, str(exc)
            )
        else:
            return common_utils.attach_file(
                album,
                "attachment_cover",
                {"content": image_data, "mimetype": "image/jpeg"},
                fetch=True,
            )


IMAGE_TYPES = [("jpg", "image/jpeg"), ("jpeg", "image/jpeg"), ("png", "image/png")]
FOLDER_IMAGE_NAMES = ["cover", "folder"]


def get_cover_from_fs(dir_path):
    if os.path.exists(dir_path):
        for name in FOLDER_IMAGE_NAMES:
            for e, m in IMAGE_TYPES:
                cover_path = os.path.join(dir_path, "{}.{}".format(name, e))
                if not os.path.exists(cover_path):
                    logger.debug("Cover %s does not exists", cover_path)
                    continue
                with open(cover_path, "rb") as c:
                    logger.info("Found cover at %s", cover_path)
                    return {"mimetype": m, "content": c.read()}


@celery.app.task(name="music.start_library_scan")
@celery.require_instance(
    models.LibraryScan.objects.select_related().filter(status="pending"), "library_scan"
)
def start_library_scan(library_scan):
    try:
        data = lb.get_library_data(library_scan.library.fid, actor=library_scan.actor)
    except Exception:
        library_scan.status = "errored"
        library_scan.save(update_fields=["status", "modification_date"])
        raise
    library_scan.modification_date = timezone.now()
    library_scan.status = "scanning"
    library_scan.total_files = data["totalItems"]
    library_scan.save(update_fields=["status", "modification_date", "total_files"])
    scan_library_page.delay(library_scan_id=library_scan.pk, page_url=data["first"])


@celery.app.task(
    name="music.scan_library_page",
    retry_backoff=60,
    max_retries=5,
    autoretry_for=[RequestException],
)
@celery.require_instance(
    models.LibraryScan.objects.select_related().filter(status="scanning"),
    "library_scan",
)
def scan_library_page(library_scan, page_url):
    data = lb.get_library_page(library_scan.library, page_url, library_scan.actor)
    uploads = []

    for item_serializer in data["items"]:
        upload = item_serializer.save(library=library_scan.library)
        uploads.append(upload)

    library_scan.processed_files = F("processed_files") + len(uploads)
    library_scan.modification_date = timezone.now()
    update_fields = ["modification_date", "processed_files"]

    next_page = data.get("next")
    fetch_next = next_page and next_page != page_url

    if not fetch_next:
        update_fields.append("status")
        library_scan.status = "finished"
    library_scan.save(update_fields=update_fields)

    if fetch_next:
        scan_library_page.delay(library_scan_id=library_scan.pk, page_url=next_page)


def getter(data, *keys, default=None):
    if not data:
        return default
    v = data
    for k in keys:
        try:
            v = v[k]
        except KeyError:
            return default

    return v


class UploadImportError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def fail_import(upload, error_code, detail=None, **fields):
    old_status = upload.import_status
    upload.import_status = "errored"
    upload.import_details = {"error_code": error_code, "detail": detail}
    upload.import_details.update(fields)
    upload.import_date = timezone.now()
    upload.save(update_fields=["import_details", "import_status", "import_date"])

    broadcast = getter(
        upload.import_metadata, "funkwhale", "config", "broadcast", default=True
    )
    if broadcast:
        signals.upload_import_status_updated.send(
            old_status=old_status,
            new_status=upload.import_status,
            upload=upload,
            sender=None,
        )


@celery.app.task(name="music.process_upload")
@celery.require_instance(
    models.Upload.objects.filter(import_status="pending").select_related(
        "library__actor__user", "library__channel__artist",
    ),
    "upload",
)
def process_upload(upload, update_denormalization=True):
    """
    Main handler to process uploads submitted by user and create the corresponding
    metadata (tracks/artists/albums) in our DB.
    """
    from . import serializers

    channel = upload.library.get_channel()
    # When upload is linked to a channel instead of a library
    # we willingly ignore the metadata embedded in the file itself
    # and rely on user metadata only
    use_file_metadata = channel is None

    import_metadata = upload.import_metadata or {}
    internal_config = {"funkwhale": import_metadata.get("funkwhale", {})}
    forced_values_serializer = serializers.ImportMetadataSerializer(
        data=import_metadata,
        context={"actor": upload.library.actor, "channel": channel},
    )
    if forced_values_serializer.is_valid():
        forced_values = forced_values_serializer.validated_data
    else:
        forced_values = {}
        if not use_file_metadata:
            detail = forced_values_serializer.errors
            metadata_dump = import_metadata
            return fail_import(
                upload, "invalid_metadata", detail=detail, file_metadata=metadata_dump
            )

    if channel:
        # ensure the upload is associated with the channel artist
        forced_values["artist"] = upload.library.channel.artist

    old_status = upload.import_status
    additional_data = {"upload_source": upload.source}

    if use_file_metadata:
        audio_file = upload.get_audio_file()

        m = metadata.Metadata(audio_file)
        try:
            serializer = metadata.TrackMetadataSerializer(data=m)
            serializer.is_valid()
        except Exception:
            fail_import(upload, "unknown_error")
            raise
        if not serializer.is_valid():
            detail = serializer.errors
            try:
                metadata_dump = m.all()
            except Exception as e:
                logger.warn("Cannot dump metadata for file %s: %s", audio_file, str(e))
            return fail_import(
                upload, "invalid_metadata", detail=detail, file_metadata=metadata_dump
            )

        final_metadata = collections.ChainMap(
            additional_data, serializer.validated_data, internal_config
        )
    else:
        final_metadata = collections.ChainMap(
            additional_data, forced_values, internal_config,
        )
    try:
        track = get_track_from_import_metadata(
            final_metadata, attributed_to=upload.library.actor, **forced_values
        )
    except UploadImportError as e:
        return fail_import(upload, e.code)
    except Exception:
        fail_import(upload, "unknown_error")
        raise

    # under some situations, we want to skip the import (
    # for instance if the user already owns the files)
    owned_duplicates = get_owned_duplicates(upload, track)
    upload.track = track

    if owned_duplicates:
        upload.import_status = "skipped"
        upload.import_details = {
            "code": "already_imported_in_owned_libraries",
            "duplicates": list(owned_duplicates),
        }
        upload.import_date = timezone.now()
        upload.save(
            update_fields=["import_details", "import_status", "import_date", "track"]
        )
        signals.upload_import_status_updated.send(
            old_status=old_status,
            new_status=upload.import_status,
            upload=upload,
            sender=None,
        )
        return

    # all is good, let's finalize the import
    audio_data = upload.get_audio_data()
    if audio_data:
        upload.duration = audio_data["duration"]
        upload.size = audio_data["size"]
        upload.bitrate = audio_data["bitrate"]
    upload.import_status = "finished"
    upload.import_date = timezone.now()
    upload.save(
        update_fields=[
            "track",
            "import_status",
            "import_date",
            "size",
            "duration",
            "bitrate",
        ]
    )
    if channel:
        common_utils.update_modification_date(channel.artist)

    if update_denormalization:
        models.TrackActor.create_entries(
            library=upload.library,
            upload_and_track_ids=[(upload.pk, upload.track_id)],
            delete_existing=False,
        )

    # update album cover, if needed
    if track.album and not track.album.attachment_cover:
        populate_album_cover(
            track.album, source=final_metadata.get("upload_source"),
        )

    broadcast = getter(
        internal_config, "funkwhale", "config", "broadcast", default=True
    )
    if broadcast:
        signals.upload_import_status_updated.send(
            old_status=old_status,
            new_status=upload.import_status,
            upload=upload,
            sender=None,
        )
    dispatch_outbox = getter(
        internal_config, "funkwhale", "config", "dispatch_outbox", default=True
    )
    if dispatch_outbox:
        routes.outbox.dispatch(
            {"type": "Create", "object": {"type": "Audio"}}, context={"upload": upload}
        )


def get_cover(obj, field):
    cover = obj.get(field)
    if cover:
        try:
            url = cover["url"]
        except KeyError:
            url = cover["href"]

        return {"mimetype": cover["mediaType"], "url": url}


def federation_audio_track_to_metadata(payload, references):
    """
    Given a valid payload as returned by federation.serializers.TrackSerializer.validated_data,
    returns a correct metadata payload for use with get_track_from_import_metadata.
    """
    new_data = {
        "title": payload["name"],
        "position": payload.get("position") or 1,
        "disc_number": payload.get("disc"),
        "license": payload.get("license"),
        "copyright": payload.get("copyright"),
        "description": payload.get("description"),
        "attributed_to": references.get(payload.get("attributedTo")),
        "mbid": str(payload.get("musicbrainzId"))
        if payload.get("musicbrainzId")
        else None,
        "cover_data": get_cover(payload, "image"),
        "album": {
            "title": payload["album"]["name"],
            "fdate": payload["album"]["published"],
            "fid": payload["album"]["id"],
            "description": payload["album"].get("description"),
            "attributed_to": references.get(payload["album"].get("attributedTo")),
            "mbid": str(payload["album"]["musicbrainzId"])
            if payload["album"].get("musicbrainzId")
            else None,
            "cover_data": get_cover(payload["album"], "cover"),
            "release_date": payload["album"].get("released"),
            "tags": [t["name"] for t in payload["album"].get("tags", []) or []],
            "artists": [
                {
                    "fid": a["id"],
                    "name": a["name"],
                    "fdate": a["published"],
                    "cover_data": get_cover(a, "image"),
                    "description": a.get("description"),
                    "attributed_to": references.get(a.get("attributedTo")),
                    "mbid": str(a["musicbrainzId"]) if a.get("musicbrainzId") else None,
                    "tags": [t["name"] for t in a.get("tags", []) or []],
                }
                for a in payload["album"]["artists"]
            ],
        },
        "artists": [
            {
                "fid": a["id"],
                "name": a["name"],
                "fdate": a["published"],
                "description": a.get("description"),
                "attributed_to": references.get(a.get("attributedTo")),
                "mbid": str(a["musicbrainzId"]) if a.get("musicbrainzId") else None,
                "tags": [t["name"] for t in a.get("tags", []) or []],
                "cover_data": get_cover(a, "image"),
            }
            for a in payload["artists"]
        ],
        # federation
        "fid": payload["id"],
        "fdate": payload["published"],
        "tags": [t["name"] for t in payload.get("tags", []) or []],
    }
    return new_data


def get_owned_duplicates(upload, track):
    """
    Ensure we skip duplicate tracks to avoid wasting user/instance storage
    """
    owned_libraries = upload.library.actor.libraries.all()
    return (
        models.Upload.objects.filter(
            track__isnull=False, library__in=owned_libraries, track=track
        )
        .exclude(pk=upload.pk)
        .values_list("uuid", flat=True)
    )


def get_best_candidate_or_create(model, query, defaults, sort_fields):
    """
    Like queryset.get_or_create() but does not crash if multiple objects
    are returned on the get() call
    """
    candidates = model.objects.filter(query)
    if candidates:

        return sort_candidates(candidates, sort_fields)[0], False

    return model.objects.create(**defaults), True


def sort_candidates(candidates, important_fields):
    """
    Given a list of objects and a list of fields,
    will return a sorted list of those objects by score.

    Score is higher for objects that have a non-empty attribute
    that is also present in important fields::

        artist1 = Artist(mbid=None, fid=None)
        artist2 = Artist(mbid="something", fid=None)

        # artist2 has a mbid, so is sorted first
        assert sort_candidates([artist1, artist2], ['mbid'])[0] == artist2

    Only supports string fields.
    """

    # map each fields to its score, giving a higher score to first fields
    fields_scores = {f: i + 1 for i, f in enumerate(sorted(important_fields))}
    candidates_with_scores = []
    for candidate in candidates:
        current_score = 0
        for field, score in fields_scores.items():
            v = getattr(candidate, field, "")
            if v:
                current_score += score

        candidates_with_scores.append((candidate, current_score))

    return [c for c, s in reversed(sorted(candidates_with_scores, key=lambda v: v[1]))]


@transaction.atomic
def get_track_from_import_metadata(
    data, update_cover=False, attributed_to=None, **forced_values
):
    track = _get_track(data, attributed_to=attributed_to, **forced_values)
    if update_cover and track and not track.album.attachment_cover:
        populate_album_cover(track.album, source=data.get("upload_source"))
    return track


def truncate(v, length):
    if v is None:
        return v
    return v[:length]


def _get_track(data, attributed_to=None, **forced_values):
    track_uuid = getter(data, "funkwhale", "track", "uuid")

    if track_uuid:
        # easy case, we have a reference to a uuid of a track that
        # already exists in our database
        try:
            track = models.Track.objects.get(uuid=track_uuid)
        except models.Track.DoesNotExist:
            raise UploadImportError(code="track_uuid_not_found")

        return track

    from_activity_id = data.get("from_activity_id", None)
    track_mbid = (
        forced_values["mbid"] if "mbid" in forced_values else data.get("mbid", None)
    )
    try:
        album_mbid = getter(data, "album", "mbid")
    except TypeError:
        # album is forced
        album_mbid = None
    track_fid = getter(data, "fid")

    query = None

    if album_mbid and track_mbid:
        query = Q(mbid=track_mbid, album__mbid=album_mbid)

    if track_fid:
        query = query | Q(fid=track_fid) if query else Q(fid=track_fid)

    if query:
        # second easy case: we have a (track_mbid, album_mbid) pair or
        # a federation uuid we can check on
        try:
            return sort_candidates(models.Track.objects.filter(query), ["mbid", "fid"])[
                0
            ]
        except IndexError:
            pass

    # get / create artist and album artist
    if "artist" in forced_values:
        artist = forced_values["artist"]
    else:
        artists = getter(data, "artists", default=[])
        artist_data = artists[0]
        artist_mbid = artist_data.get("mbid", None)
        artist_fid = artist_data.get("fid", None)
        artist_name = truncate(artist_data["name"], models.MAX_LENGTHS["ARTIST_NAME"])

        if artist_mbid:
            query = Q(mbid=artist_mbid)
        else:
            query = Q(name__iexact=artist_name)
        if artist_fid:
            query |= Q(fid=artist_fid)
        defaults = {
            "name": artist_name,
            "mbid": artist_mbid,
            "fid": artist_fid,
            "from_activity_id": from_activity_id,
            "attributed_to": artist_data.get("attributed_to", attributed_to),
        }
        if artist_data.get("fdate"):
            defaults["creation_date"] = artist_data.get("fdate")

        artist, created = get_best_candidate_or_create(
            models.Artist, query, defaults=defaults, sort_fields=["mbid", "fid"]
        )
        if created:
            tags_models.add_tags(artist, *artist_data.get("tags", []))
            common_utils.attach_content(
                artist, "description", artist_data.get("description")
            )
            common_utils.attach_file(
                artist, "attachment_cover", artist_data.get("cover_data")
            )

    if "album" in forced_values:
        album = forced_values["album"]
    else:
        if "artist" in forced_values:
            album_artist = forced_values["artist"]
        else:
            album_artists = getter(data, "album", "artists", default=artists) or artists
            album_artist_data = album_artists[0]
            album_artist_name = truncate(
                album_artist_data.get("name"), models.MAX_LENGTHS["ARTIST_NAME"]
            )
            if album_artist_name == artist_name:
                album_artist = artist
            else:
                query = Q(name__iexact=album_artist_name)
                album_artist_mbid = album_artist_data.get("mbid", None)
                album_artist_fid = album_artist_data.get("fid", None)
                if album_artist_mbid:
                    query |= Q(mbid=album_artist_mbid)
                if album_artist_fid:
                    query |= Q(fid=album_artist_fid)
                defaults = {
                    "name": album_artist_name,
                    "mbid": album_artist_mbid,
                    "fid": album_artist_fid,
                    "from_activity_id": from_activity_id,
                    "attributed_to": album_artist_data.get(
                        "attributed_to", attributed_to
                    ),
                }
                if album_artist_data.get("fdate"):
                    defaults["creation_date"] = album_artist_data.get("fdate")

                album_artist, created = get_best_candidate_or_create(
                    models.Artist, query, defaults=defaults, sort_fields=["mbid", "fid"]
                )
                if created:
                    tags_models.add_tags(
                        album_artist, *album_artist_data.get("tags", [])
                    )
                    common_utils.attach_content(
                        album_artist,
                        "description",
                        album_artist_data.get("description"),
                    )
                    common_utils.attach_file(
                        album_artist,
                        "attachment_cover",
                        album_artist_data.get("cover_data"),
                    )

        # get / create album
        if "album" in data:
            album_data = data["album"]
            album_title = truncate(
                album_data["title"], models.MAX_LENGTHS["ALBUM_TITLE"]
            )
            album_fid = album_data.get("fid", None)

            if album_mbid:
                query = Q(mbid=album_mbid)
            else:
                query = Q(title__iexact=album_title, artist=album_artist)

            if album_fid:
                query |= Q(fid=album_fid)
            defaults = {
                "title": album_title,
                "artist": album_artist,
                "mbid": album_mbid,
                "release_date": album_data.get("release_date"),
                "fid": album_fid,
                "from_activity_id": from_activity_id,
                "attributed_to": album_data.get("attributed_to", attributed_to),
            }
            if album_data.get("fdate"):
                defaults["creation_date"] = album_data.get("fdate")

            album, created = get_best_candidate_or_create(
                models.Album, query, defaults=defaults, sort_fields=["mbid", "fid"]
            )
            if created:
                tags_models.add_tags(album, *album_data.get("tags", []))
                common_utils.attach_content(
                    album, "description", album_data.get("description")
                )
                common_utils.attach_file(
                    album, "attachment_cover", album_data.get("cover_data")
                )
        else:
            album = None
    # get / create track
    track_title = (
        forced_values["title"]
        if "title" in forced_values
        else truncate(data["title"], models.MAX_LENGTHS["TRACK_TITLE"])
    )
    position = (
        forced_values["position"]
        if "position" in forced_values
        else data.get("position", 1)
    )
    disc_number = (
        forced_values["disc_number"]
        if "disc_number" in forced_values
        else data.get("disc_number")
    )
    license = (
        forced_values["license"]
        if "license" in forced_values
        else licenses.match(data.get("license"), data.get("copyright"))
    )
    copyright = (
        forced_values["copyright"]
        if "copyright" in forced_values
        else truncate(data.get("copyright"), models.MAX_LENGTHS["COPYRIGHT"])
    )
    description = (
        {"text": forced_values["description"], "content_type": "text/markdown"}
        if "description" in forced_values
        else data.get("description")
    )
    cover_data = (
        forced_values["cover"] if "cover" in forced_values else data.get("cover_data")
    )

    query = Q(
        title__iexact=track_title,
        artist=artist,
        album=album,
        position=position,
        disc_number=disc_number,
    )
    if track_mbid:
        if album_mbid:
            query |= Q(mbid=track_mbid, album__mbid=album_mbid)
        else:
            query |= Q(mbid=track_mbid)
    if track_fid:
        query |= Q(fid=track_fid)

    defaults = {
        "title": track_title,
        "album": album,
        "mbid": track_mbid,
        "artist": artist,
        "position": position,
        "disc_number": disc_number,
        "fid": track_fid,
        "from_activity_id": from_activity_id,
        "attributed_to": data.get("attributed_to", attributed_to),
        "license": license,
        "copyright": copyright,
    }
    if data.get("fdate"):
        defaults["creation_date"] = data.get("fdate")

    track, created = get_best_candidate_or_create(
        models.Track, query, defaults=defaults, sort_fields=["mbid", "fid"]
    )

    if created:
        tags = (
            forced_values["tags"] if "tags" in forced_values else data.get("tags", [])
        )
        tags_models.add_tags(track, *tags)
        common_utils.attach_content(track, "description", description)
        common_utils.attach_file(track, "attachment_cover", cover_data)

    return track


@receiver(signals.upload_import_status_updated)
def broadcast_import_status_update_to_owner(old_status, new_status, upload, **kwargs):
    user = upload.library.actor.get_user()
    if not user:
        return

    from . import serializers

    group = "user.{}.imports".format(user.pk)
    channels.group_send(
        group,
        {
            "type": "event.send",
            "text": "",
            "data": {
                "type": "import.status_updated",
                "upload": serializers.UploadForOwnerSerializer(upload).data,
                "old_status": old_status,
                "new_status": new_status,
            },
        },
    )


@celery.app.task(name="music.clean_transcoding_cache")
def clean_transcoding_cache():
    delay = preferences.get("music__transcoding_cache_duration")
    if delay < 1:
        return  # cache clearing disabled
    limit = timezone.now() - datetime.timedelta(minutes=delay)
    candidates = (
        models.UploadVersion.objects.filter(
            (Q(accessed_date__lt=limit) | Q(accessed_date=None))
        )
        .only("audio_file", "id")
        .order_by("id")
    )
    return candidates.delete()


@celery.app.task(name="music.albums_set_tags_from_tracks")
@transaction.atomic
def albums_set_tags_from_tracks(ids=None, dry_run=False):
    qs = models.Album.objects.filter(tagged_items__isnull=True).order_by("id")
    qs = federation_utils.local_qs(qs)
    qs = qs.values_list("id", flat=True)
    if ids is not None:
        qs = qs.filter(pk__in=ids)
    data = tags_tasks.get_tags_from_foreign_key(
        ids=qs, foreign_key_model=models.Track, foreign_key_attr="album",
    )
    logger.info("Found automatic tags for %s albums…", len(data))
    if dry_run:
        logger.info("Running in dry-run mode, not commiting")
        return

    tags_tasks.add_tags_batch(
        data, model=models.Album,
    )
    return data


@celery.app.task(name="music.artists_set_tags_from_tracks")
@transaction.atomic
def artists_set_tags_from_tracks(ids=None, dry_run=False):
    qs = models.Artist.objects.filter(tagged_items__isnull=True).order_by("id")
    qs = federation_utils.local_qs(qs)
    qs = qs.values_list("id", flat=True)
    if ids is not None:
        qs = qs.filter(pk__in=ids)
    data = tags_tasks.get_tags_from_foreign_key(
        ids=qs, foreign_key_model=models.Track, foreign_key_attr="artist",
    )
    logger.info("Found automatic tags for %s artists…", len(data))
    if dry_run:
        logger.info("Running in dry-run mode, not commiting")
        return

    tags_tasks.add_tags_batch(
        data, model=models.Artist,
    )
    return data


def get_prunable_tracks(
    exclude_favorites=True, exclude_playlists=True, exclude_listenings=True
):
    """
    Returns a list of tracks with no associated uploads,
    excluding the one that were listened/favorited/included in playlists.
    """
    purgeable_tracks_with_upload = (
        models.Upload.objects.exclude(track=None)
        .filter(import_status="skipped")
        .values("track")
    )
    queryset = models.Track.objects.all()
    queryset = queryset.filter(
        Q(uploads__isnull=True) | Q(pk__in=purgeable_tracks_with_upload)
    )
    if exclude_favorites:
        queryset = queryset.filter(track_favorites__isnull=True)
    if exclude_playlists:
        queryset = queryset.filter(playlist_tracks__isnull=True)
    if exclude_listenings:
        queryset = queryset.filter(listenings__isnull=True)

    return queryset


def get_prunable_albums():
    return models.Album.objects.filter(tracks__isnull=True)


def get_prunable_artists():
    return models.Artist.objects.filter(tracks__isnull=True, albums__isnull=True)


def update_library_entity(obj, data):
    """
    Given an obj and some updated fields, will persist the changes on the obj
    and also check if the entity need to be aliased with existing objs (i.e
    if a mbid was added on the obj, and match another entity with the same mbid)
    """
    for key, value in data.items():
        setattr(obj, key, value)

    # Todo: handle integrity error on unique fields (such as MBID)
    obj.save(update_fields=list(data.keys()))

    return obj


UPDATE_CONFIG = {
    "track": {
        "position": {},
        "title": {},
        "mbid": {},
        "disc_number": {},
        "copyright": {},
        "license": {
            "getter": lambda data, field: licenses.match(
                data.get("license"), data.get("copyright")
            )
        },
    },
    "album": {"title": {}, "mbid": {}, "release_date": {}},
    "artist": {"name": {}, "mbid": {}},
    "album_artist": {"name": {}, "mbid": {}},
}


@transaction.atomic
def update_track_metadata(audio_metadata, track):
    # XXX: implement this to support updating metadata when an imported files
    # is updated by an outside tool (e.g beets).
    serializer = metadata.TrackMetadataSerializer(data=audio_metadata)
    serializer.is_valid(raise_exception=True)
    new_data = serializer.validated_data

    to_update = [
        ("track", track, lambda data: data),
        ("album", track.album, lambda data: data["album"]),
        ("artist", track.artist, lambda data: data["artists"][0]),
        (
            "album_artist",
            track.album.artist if track.album else None,
            lambda data: data["album"]["artists"][0],
        ),
    ]
    for id, obj, data_getter in to_update:
        if not obj:
            continue
        obj_updated_fields = []
        try:
            obj_data = data_getter(new_data)
        except IndexError:
            continue
        for field, config in UPDATE_CONFIG[id].items():
            getter = config.get(
                "getter", lambda data, field: data[config.get("field", field)]
            )
            try:
                new_value = getter(obj_data, field)
            except KeyError:
                continue
            old_value = getattr(obj, field)
            if new_value == old_value:
                continue
            obj_updated_fields.append(field)
            setattr(obj, field, new_value)

        if obj_updated_fields:
            obj.save(update_fields=obj_updated_fields)

    if track.album and "album" in new_data and new_data["album"].get("cover_data"):
        common_utils.attach_file(
            track.album, "attachment_cover", new_data["album"].get("cover_data")
        )

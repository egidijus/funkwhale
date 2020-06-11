import collections
import datetime
import itertools
import os
import queue
import threading
import time
import urllib.parse

import watchdog.events
import watchdog.observers

from django.conf import settings
from django.core.files import File
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from rest_framework import serializers

from funkwhale_api.common import utils as common_utils
from funkwhale_api.music import models, tasks, utils


def crawl_dir(dir, extensions, recursive=True, ignored=[]):
    if os.path.isfile(dir):
        yield dir
        return
    try:
        scanner = os.scandir(dir)
        for entry in scanner:
            if entry.is_file():
                for e in extensions:
                    if entry.name.lower().endswith(".{}".format(e.lower())):
                        if entry.path not in ignored:
                            yield entry.path
            elif recursive and entry.is_dir():
                yield from crawl_dir(
                    entry.path, extensions, recursive=recursive, ignored=ignored
                )
    finally:
        if hasattr(scanner, "close"):
            scanner.close()


def batch(iterable, n=1):
    has_entries = True
    while has_entries:
        current = []
        for i in range(0, n):
            try:
                current.append(next(iterable))
            except StopIteration:
                has_entries = False
        yield current


class Command(BaseCommand):
    help = "Import audio files mathinc given glob pattern"

    def add_arguments(self, parser):
        parser.add_argument(
            "library_id",
            type=str,
            help=(
                "A local library identifier where the files should be imported. "
                "You can use the full uuid such as e29c5be9-6da3-4d92-b40b-4970edd3ee4b "
                "or only a small portion of it, starting from the beginning, such as "
                "e29c5be9"
            ),
        )
        parser.add_argument("path", nargs="+", type=str)
        parser.add_argument(
            "--recursive",
            action="store_true",
            dest="recursive",
            default=False,
            help="Will match the pattern recursively (including subdirectories)",
        )
        parser.add_argument(
            "--username",
            dest="username",
            help="The username of the user you want to be bound to the import",
        )
        parser.add_argument(
            "--async",
            action="store_true",
            dest="async_",
            default=False,
            help="Will launch celery tasks for each file to import instead of doing it synchronously and block the CLI",
        )
        parser.add_argument(
            "--exit",
            "-x",
            action="store_true",
            dest="exit_on_failure",
            default=False,
            help="Use this flag to disable error catching",
        )
        parser.add_argument(
            "--in-place",
            "-i",
            action="store_true",
            dest="in_place",
            default=False,
            help=(
                "Import files without duplicating them into the media directory."
                "For in-place import to work, the music files must be readable"
                "by the web-server and funkwhale api and celeryworker processes."
                "You may want to use this if you have a big music library to "
                "import and not much disk space available."
            ),
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            dest="replace",
            default=False,
            help=(
                "Use this flag to replace duplicates (tracks with same "
                "musicbrainz mbid, or same artist, album and title) on import "
                "with their newest version."
            ),
        )
        parser.add_argument(
            "--outbox",
            action="store_true",
            dest="outbox",
            default=False,
            help=(
                "Use this flag to notify library followers of newly imported files. "
                "You'll likely want to keep this disabled for CLI imports, especially if"
                "you plan to import hundreds or thousands of files, as it will cause a lot "
                "of overhead on your server and on servers you are federating with."
            ),
        )
        parser.add_argument(
            "--watch",
            action="store_true",
            dest="watch",
            default=False,
            help=(
                "Start the command in watch mode. Instead of running a full import, "
                "and exit, watch the given path and import new files, remove deleted "
                "files, and update metadata corresponding to updated files."
            ),
        )
        parser.add_argument("-e", "--extension", nargs="+")

        parser.add_argument(
            "--broadcast",
            action="store_true",
            dest="broadcast",
            default=False,
            help=(
                "Use this flag to enable realtime updates about the import in the UI. "
                "This causes some overhead, so it's disabled by default."
            ),
        )
        parser.add_argument(
            "--prune",
            action="store_true",
            dest="prune",
            default=False,
            help=(
                "Once the import is completed, prune tracks, ablums and artists that aren't linked to any upload."
            ),
        )

        parser.add_argument(
            "--reference",
            action="store",
            dest="reference",
            default=None,
            help=(
                "A custom reference for the import. Leave this empty to have a random "
                "reference being generated for you."
            ),
        )
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Do NOT prompt the user for input of any kind.",
        )

        parser.add_argument(
            "--batch-size",
            "-s",
            dest="batch_size",
            default=1000,
            type=int,
            help="Size of each batch, only used when crawling large collections",
        )

    def handle(self, *args, **options):
        # handle relative directories
        options["path"] = [os.path.abspath(path) for path in options["path"]]
        self.is_confirmed = False
        try:
            library = models.Library.objects.select_related("actor__user").get(
                uuid__startswith=options["library_id"]
            )
        except models.Library.DoesNotExist:
            raise CommandError("Invalid library id")

        if not library.actor.get_user():
            raise CommandError("Library {} is not a local library".format(library.uuid))

        if options["in_place"]:
            self.stdout.write(
                "Checking imported paths against settings.MUSIC_DIRECTORY_PATH"
            )

            for import_path in options["path"]:
                p = settings.MUSIC_DIRECTORY_PATH
                if not p:
                    raise CommandError(
                        "Importing in-place requires setting the "
                        "MUSIC_DIRECTORY_PATH variable"
                    )
                if p and not import_path.startswith(p):
                    raise CommandError(
                        "Importing in-place only works if importing "
                        "from {} (MUSIC_DIRECTORY_PATH), as this directory"
                        "needs to be accessible by the webserver."
                        "Culprit: {}".format(p, import_path)
                    )

        reference = options["reference"] or "cli-{}".format(timezone.now().isoformat())

        import_url = "{}://{}/library/{}/upload?{}"
        import_url = import_url.format(
            settings.FUNKWHALE_PROTOCOL,
            settings.FUNKWHALE_HOSTNAME,
            str(library.uuid),
            urllib.parse.urlencode([("import", reference)]),
        )
        self.stdout.write(
            "For details, please refer to import reference '{}' or URL {}".format(
                reference, import_url
            )
        )
        extensions = options.get("extension") or utils.SUPPORTED_EXTENSIONS
        if options["watch"]:
            if len(options["path"]) > 1:
                raise CommandError("Watch only work with a single directory")

            return self.setup_watcher(
                extensions=extensions,
                path=options["path"][0],
                reference=reference,
                library=library,
                in_place=options["in_place"],
                prune=options["prune"],
                recursive=options["recursive"],
                replace=options["replace"],
                dispatch_outbox=options["outbox"],
                broadcast=options["broadcast"],
            )

        update = True
        checked_paths = set()
        if options["in_place"] and update:
            self.stdout.write("Checking existing files for updates…")
            message = (
                "Are you sure you want to do this?\n\n"
                "Type 'yes' to continue, or 'no' to skip checking for updates in "
                "already imported files: "
            )
            if options["interactive"] and input("".join(message)) != "yes":
                pass
            else:
                checked_paths = check_updates(
                    stdout=self.stdout,
                    paths=options["path"],
                    extensions=extensions,
                    library=library,
                    batch_size=options["batch_size"],
                )
                self.stdout.write("Existing files checked, moving on to next step!")

        crawler = itertools.chain(
            *[
                crawl_dir(
                    p,
                    extensions=extensions,
                    recursive=options["recursive"],
                    ignored=checked_paths,
                )
                for p in options["path"]
            ]
        )
        errors = []
        total = 0
        start_time = time.time()
        batch_start = None
        batch_duration = None
        self.stdout.write("Starting import of new files…")
        for i, entries in enumerate(batch(crawler, options["batch_size"])):
            total += len(entries)
            batch_start = time.time()
            time_stats = ""
            if i > 0:
                time_stats = " - running for {}s, previous batch took {}s".format(
                    int(time.time() - start_time), int(batch_duration),
                )
            if entries:
                self.stdout.write(
                    "Handling batch {} ({} items){}".format(
                        i + 1, len(entries), time_stats,
                    )
                )
                batch_errors = self.handle_batch(
                    library=library,
                    paths=entries,
                    batch=i + 1,
                    reference=reference,
                    options=options,
                )
                if batch_errors:
                    errors += batch_errors

            batch_duration = time.time() - batch_start

        message = "Successfully imported {} new tracks in {}s"
        if options["async_"]:
            message = "Successfully launched import for {} new tracks in {}s"

        self.stdout.write(
            message.format(total - len(errors), int(time.time() - start_time))
        )
        if len(errors) > 0:
            self.stderr.write("{} tracks could not be imported:".format(len(errors)))

            for path, error in errors:
                self.stderr.write("- {}: {}".format(path, error))

        self.stdout.write(
            "For details, please refer to import reference '{}' or URL {}".format(
                reference, import_url
            )
        )

        if options["prune"]:
            self.stdout.write(
                "Pruning dangling tracks, albums and artists from library…"
            )
            prune()

    def handle_batch(self, library, paths, batch, reference, options):
        matching = []
        for m in paths:
            # In some situations, the path is encoded incorrectly on the filesystem
            # so we filter out faulty paths and display a warning to the user.
            # see https://dev.funkwhale.audio/funkwhale/funkwhale/issues/138
            try:
                m.encode("utf-8")
                matching.append(m)
            except UnicodeEncodeError:
                try:
                    previous = matching[-1]
                except IndexError:
                    previous = None
                self.stderr.write(
                    self.style.WARNING(
                        "[warning] Ignoring undecodable path. Previous ok file was {}".format(
                            previous
                        )
                    )
                )

        if not matching:
            raise CommandError("No file matching pattern, aborting")

        if options["replace"]:
            filtered = {"initial": matching, "skipped": [], "new": matching}
            message = "  - {} files to be replaced"
            import_paths = matching
        else:
            filtered = self.filter_matching(matching, library)
            message = "  - {} files already found in database"
            import_paths = filtered["new"]

        self.stdout.write("  Import summary:")
        self.stdout.write(
            "  - {} files found matching this pattern: {}".format(
                len(matching), options["path"]
            )
        )
        self.stdout.write(message.format(len(filtered["skipped"])))

        self.stdout.write("  - {} new files".format(len(filtered["new"])))

        if batch == 1:
            self.stdout.write(
                "  Selected options: {}".format(
                    ", ".join(
                        ["in place" if options["in_place"] else "copy music files"]
                    )
                )
            )
        if len(filtered["new"]) == 0:
            self.stdout.write("  Nothing new to import, exiting")
            return

        if options["interactive"] and not self.is_confirmed:
            message = (
                "Are you sure you want to do this?\n\n"
                "Type 'yes' to continue, or 'no' to cancel: "
            )
            if input("".join(message)) != "yes":
                raise CommandError("Import cancelled.")
            self.is_confirmed = True

        errors = self.do_import(
            import_paths,
            library=library,
            reference=reference,
            batch=batch,
            options=options,
        )
        return errors

    def filter_matching(self, matching, library):
        sources = ["file://{}".format(p) for p in matching]
        # we skip reimport for path that are already found
        # as a Upload.source
        existing = library.uploads.filter(source__in=sources, import_status="finished")
        existing = existing.values_list("source", flat=True)
        existing = set([p.replace("file://", "", 1) for p in existing])
        skipped = set(matching) & existing
        result = {
            "initial": matching,
            "skipped": list(sorted(skipped)),
            "new": list(sorted(set(matching) - skipped)),
        }
        return result

    def do_import(self, paths, library, reference, batch, options):
        message = "[batch {batch}] {i}/{total} Importing {path}..."
        if options["async_"]:
            message = "[batch {batch}] {i}/{total} Launching import for {path}..."

        # we create an upload binded to the library
        async_ = options["async_"]
        errors = []
        for i, path in list(enumerate(paths)):
            if options["verbosity"] > 1:
                self.stdout.write(
                    message.format(batch=batch, path=path, i=i + 1, total=len(paths))
                )
            try:
                create_upload(
                    path=path,
                    reference=reference,
                    library=library,
                    async_=async_,
                    replace=options["replace"],
                    in_place=options["in_place"],
                    dispatch_outbox=options["outbox"],
                    broadcast=options["broadcast"],
                )
            except Exception as e:
                if options["exit_on_failure"]:
                    raise
                m = "Error while importing {}: {} {}".format(
                    path, e.__class__.__name__, e
                )
                self.stderr.write(m)
                errors.append((path, "{} {}".format(e.__class__.__name__, e)))
        return errors

    def setup_watcher(self, path, extensions, recursive, **kwargs):
        watchdog_queue = queue.Queue()
        # Set up a worker thread to process database load
        worker = threading.Thread(
            target=process_load_queue(self.stdout, **kwargs), args=(watchdog_queue,),
        )
        worker.setDaemon(True)
        worker.start()

        # setup watchdog to monitor directory for trigger files
        patterns = ["*.{}".format(e) for e in extensions]
        event_handler = Watcher(
            stdout=self.stdout, queue=watchdog_queue, patterns=patterns,
        )
        observer = watchdog.observers.Observer()
        observer.schedule(event_handler, path, recursive=recursive)
        observer.start()

        try:
            while True:
                self.stdout.write(
                    "Watching for changes at {}…".format(path), ending="\r"
                )
                time.sleep(10)
                if kwargs["prune"] and GLOBAL["need_pruning"]:
                    self.stdout.write("Some files were deleted, pruning library…")
                    prune()
                    GLOBAL["need_pruning"] = False
        except KeyboardInterrupt:
            self.stdout.write("Exiting…")
            observer.stop()

        observer.join()


GLOBAL = {"need_pruning": False}


def prune():
    call_command(
        "prune_library",
        dry_run=False,
        prune_artists=True,
        prune_albums=True,
        prune_tracks=True,
    )


def create_upload(
    path, reference, library, async_, replace, in_place, dispatch_outbox, broadcast,
):
    import_handler = tasks.process_upload.delay if async_ else tasks.process_upload
    upload = models.Upload(library=library, import_reference=reference)
    upload.source = "file://" + path
    upload.import_metadata = {
        "funkwhale": {
            "config": {
                "replace": replace,
                "dispatch_outbox": dispatch_outbox,
                "broadcast": broadcast,
            }
        }
    }
    if not in_place:
        name = os.path.basename(path)
        with open(path, "rb") as f:
            upload.audio_file.save(name, File(f), save=False)

    upload.save()

    import_handler(upload_id=upload.pk)


def process_load_queue(stdout, **kwargs):
    def inner(q):
        # we batch events, to avoid calling same methods multiple times if a file is modified
        # a lot in a really short time
        flush_delay = 2
        batched_events = collections.OrderedDict()
        while True:
            while True:
                if not q.empty():
                    event = q.get()
                    batched_events[event["path"]] = event
                else:
                    break
            for path, event in batched_events.copy().items():
                if time.time() - event["time"] <= flush_delay:
                    continue
                now = datetime.datetime.utcnow()
                stdout.write(
                    "{} -- Processing {}:{}...\n".format(
                        now.strftime("%Y/%m/%d %H:%M:%S"), event["type"], event["path"]
                    )
                )
                del batched_events[path]
                handle_event(event, stdout=stdout, **kwargs)
            time.sleep(1)

    return inner


class Watcher(watchdog.events.PatternMatchingEventHandler):
    def __init__(self, stdout, queue, patterns):
        self.stdout = stdout
        self.queue = queue
        super().__init__(patterns=patterns)

    def enqueue(self, event):
        e = {
            "is_directory": event.is_directory,
            "type": event.event_type,
            "path": event.src_path,
            "src_path": event.src_path,
            "dest_path": getattr(event, "dest_path", None),
            "time": time.time(),
        }
        self.queue.put(e)

    def on_moved(self, event):
        self.enqueue(event)

    def on_created(self, event):
        self.enqueue(event)

    def on_deleted(self, event):
        self.enqueue(event)

    def on_modified(self, event):
        self.enqueue(event)


def handle_event(event, stdout, **kwargs):
    handlers = {
        "modified": handle_modified,
        "created": handle_created,
        "moved": handle_moved,
        "deleted": handle_deleted,
    }
    handlers[event["type"]](event=event, stdout=stdout, **kwargs)


def handle_modified(event, stdout, library, in_place, **kwargs):
    existing_candidates = library.uploads.filter(import_status="finished")
    with open(event["path"], "rb") as f:
        checksum = common_utils.get_file_hash(f)

    existing = existing_candidates.filter(checksum=checksum).first()
    if existing:
        # found an existing file with same checksum, nothing to do
        stdout.write("  File already imported and metadata is up-to-date")
        return

    to_update = None
    if in_place:
        source = "file://{}".format(event["path"])
        to_update = (
            existing_candidates.in_place()
            .filter(source=source)
            .select_related(
                "track__attributed_to", "track__artist", "track__album__artist",
            )
            .first()
        )
        if to_update:
            if (
                to_update.track.attributed_to
                and to_update.track.attributed_to != library.actor
            ):
                stdout.write(
                    "  Cannot update track metadata, track belongs to someone else".format(
                        to_update.pk
                    )
                )
                return
            else:
                stdout.write(
                    "  Updating existing file #{} with new metadata…".format(
                        to_update.pk
                    )
                )
                audio_metadata = to_update.get_metadata()
                try:
                    tasks.update_track_metadata(audio_metadata, to_update.track)
                except serializers.ValidationError as e:
                    stdout.write("  Invalid metadata: {}".format(e))
                else:
                    to_update.checksum = checksum
                    to_update.save(update_fields=["checksum"])
                return

    stdout.write("  Launching import for new file")
    create_upload(
        path=event["path"],
        reference=kwargs["reference"],
        library=library,
        async_=False,
        replace=kwargs["replace"],
        in_place=in_place,
        dispatch_outbox=kwargs["dispatch_outbox"],
        broadcast=kwargs["broadcast"],
    )


def handle_created(event, stdout, **kwargs):
    """
    Created is essentially an alias for modified, because for instance when copying a file in the watched directory,
    a created event will be fired on the initial touch, then many modified event (as the file is written).
    """
    return handle_modified(event, stdout, **kwargs)


def handle_moved(event, stdout, library, in_place, **kwargs):
    if not in_place:
        return

    old_source = "file://{}".format(event["src_path"])
    new_source = "file://{}".format(event["dest_path"])
    existing_candidates = library.uploads.filter(import_status="finished")
    existing_candidates = existing_candidates.in_place().filter(source=old_source)
    existing = existing_candidates.first()
    if existing:
        stdout.write("  Updating path of existing file #{}".format(existing.pk))
        existing.source = new_source
        existing.save(update_fields=["source"])


def handle_deleted(event, stdout, library, in_place, **kwargs):
    if not in_place:
        return
    source = "file://{}".format(event["path"])
    existing_candidates = library.uploads.filter(import_status="finished")
    existing_candidates = existing_candidates.in_place().filter(source=source)
    if existing_candidates.count():
        stdout.write("  Removing file from DB")
        existing_candidates.delete()
        GLOBAL["need_pruning"] = True


def check_updates(stdout, library, extensions, paths, batch_size):
    existing = (
        library.uploads.in_place()
        .filter(import_status="finished")
        .exclude(checksum=None)
        .select_related("library", "track")
    )
    queries = []
    checked_paths = set()
    for path in paths:
        for ext in extensions:
            queries.append(
                Q(source__startswith="file://{}".format(path))
                & Q(source__endswith=".{}".format(ext))
            )
    query, remainder = queries[0], queries[1:]
    for q in remainder:
        query = q | query
    existing = existing.filter(query)
    total = existing.count()
    stdout.write("Found {} files to check in database!".format(total))
    uploads = existing.order_by("source")
    for i, rows in enumerate(batch(uploads.iterator(), batch_size)):
        stdout.write("Handling batch {} ({} items)".format(i + 1, len(rows),))

        for upload in rows:

            check_upload(stdout, upload)
            checked_paths.add(upload.source.replace("file://", "", 1))

    return checked_paths


def check_upload(stdout, upload):
    try:
        audio_file = upload.get_audio_file()
    except FileNotFoundError:
        stdout.write(
            "  Removing file #{} missing from disk at {}".format(
                upload.pk, upload.source
            )
        )
        return upload.delete()

    checksum = common_utils.get_file_hash(audio_file)
    if upload.checksum != checksum:
        stdout.write(
            "  File #{} at {} was modified, updating metadata…".format(
                upload.pk, upload.source
            )
        )
        if upload.library.actor_id != upload.track.attributed_to_id:
            stdout.write(
                "  Cannot update track metadata, track belongs to someone else".format(
                    upload.pk
                )
            )
        else:
            track = models.Track.objects.select_related("artist", "album__artist").get(
                pk=upload.track_id
            )
            try:
                tasks.update_track_metadata(upload.get_metadata(), track)
            except serializers.ValidationError as e:
                stdout.write("  Invalid metadata: {}".format(e))
                return
            else:
                upload.checksum = checksum
                upload.save(update_fields=["checksum"])

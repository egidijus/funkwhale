from django.core.management.base import BaseCommand, CommandError

from funkwhale_api.common import utils
from funkwhale_api.federation import models as federation_models
from funkwhale_api.music import models as music_models


MODELS = [
    (music_models.Artist, ["fid"]),
    (music_models.Album, ["fid"]),
    (music_models.Track, ["fid"]),
    (music_models.Upload, ["fid"]),
    (music_models.Library, ["fid", "followers_url"]),
    (
        federation_models.Actor,
        [
            "fid",
            "url",
            "outbox_url",
            "inbox_url",
            "following_url",
            "followers_url",
            "shared_inbox_url",
        ],
    ),
    (federation_models.Activity, ["fid"]),
    (federation_models.Follow, ["fid"]),
    (federation_models.LibraryFollow, ["fid"]),
]


class Command(BaseCommand):
    help = """
    Find and replace wrong protocal/domain in local federation ids.

    Use with caution and only if you know what you are doing.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "old_base_url",
            type=str,
            help="The invalid url prefix you want to find and replace, e.g 'http://baddomain'",
        )
        parser.add_argument(
            "new_base_url",
            type=str,
            help="The url prefix you want to use in place of the bad one, e.g 'https://gooddomain'",
        )
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Do NOT prompt the user for input of any kind.",
        )

        parser.add_argument(
            "--no-dry-run",
            action="store_false",
            dest="dry_run",
            help="Commit the changes to the database",
        )

    def handle(self, *args, **options):
        results = {}
        old_prefix, new_prefix = options["old_base_url"], options["new_base_url"]
        for kls, fields in MODELS:
            results[kls] = {}
            for field in fields:
                candidates = kls.objects.filter(
                    **{"{}__startswith".format(field): old_prefix}
                )
                results[kls][field] = candidates.count()

        total = sum([t for k in results.values() for t in k.values()])
        self.stdout.write("")
        if total:
            self.stdout.write(
                self.style.WARNING(
                    "Will replace {} found occurrences of '{}' by '{}':".format(
                        total, old_prefix, new_prefix
                    )
                )
            )
            self.stdout.write("")
            for kls, fields in results.items():
                for field, count in fields.items():
                    self.stdout.write(
                        "- {}/{} {}.{}".format(
                            count, kls.objects.count(), kls._meta.label, field
                        )
                    )

        else:
            self.stdout.write(
                "No objects found with prefix {}, exiting.".format(old_prefix)
            )
            return
        if options["dry_run"]:
            self.stdout.write(
                "Run this command with --no-dry-run to perform the replacement."
            )
            return
        self.stdout.write("")
        if options["interactive"]:
            message = (
                "Are you sure you want to perform the replacement on {} objects?\n\n"
                "Type 'yes' to continue, or 'no' to cancel: "
            ).format(total)
            if input("".join(message)) != "yes":
                raise CommandError("Command canceled.")

        for kls, fields in results.items():
            for field, count in fields.items():
                self.stdout.write(
                    "Replacing {} on {} {}…".format(field, count, kls._meta.label)
                )
                candidates = kls.objects.all()
                utils.replace_prefix(candidates, field, old=old_prefix, new=new_prefix)
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Done!"))

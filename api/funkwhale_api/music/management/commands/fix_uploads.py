from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from funkwhale_api.music import models, utils


class Command(BaseCommand):
    help = "Run common checks and fix against imported tracks"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Do not execute anything",
        )
        parser.add_argument(
            "--mimetypes",
            action="store_true",
            dest="mimetypes",
            default=True,
            help="Check and fix mimetypes",
        )
        parser.add_argument(
            "--audio-data",
            action="store_true",
            dest="data",
            default=False,
            help="Check and fix bitrate and duration, can be really slow because it needs to access files",
        )
        parser.add_argument(
            "--size",
            action="store_true",
            dest="size",
            default=False,
            help="Check and fix file size, can be really slow because it needs to access files",
        )

    def handle(self, *args, **options):
        if options["dry_run"]:
            self.stdout.write("Dry-run on, will not commit anything")
        if options["mimetypes"]:
            self.fix_mimetypes(**options)
        if options["data"]:
            self.fix_file_data(**options)
        if options["size"]:
            self.fix_file_size(**options)

    @transaction.atomic
    def fix_mimetypes(self, dry_run, **kwargs):
        self.stdout.write("Fixing missing mimetypes...")
        matching = models.Upload.objects.filter(
            Q(source__startswith="file://") | Q(source__startswith="upload://")
        ).exclude(mimetype__startswith="audio/")
        self.stdout.write(
            "[mimetypes] {} entries found with bad or no mimetype".format(
                matching.count()
            )
        )
        for extension, mimetype in utils.EXTENSION_TO_MIMETYPE.items():
            qs = matching.filter(source__endswith=".{}".format(extension))
            self.stdout.write(
                "[mimetypes] setting {} {} files to {}".format(
                    qs.count(), extension, mimetype
                )
            )
            if not dry_run:
                self.stdout.write("[mimetypes] commiting...")
                qs.update(mimetype=mimetype)

    def fix_file_data(self, dry_run, **kwargs):
        self.stdout.write("Fixing missing bitrate or length...")
        matching = models.Upload.objects.filter(
            Q(bitrate__isnull=True) | Q(duration__isnull=True)
        )
        total = matching.count()
        self.stdout.write(
            "[bitrate/length] {} entries found with missing values".format(total)
        )
        if dry_run:
            return
        for i, upload in enumerate(matching.only("audio_file")):
            self.stdout.write(
                "[bitrate/length] {}/{} fixing file #{}".format(i + 1, total, upload.pk)
            )

            try:
                audio_file = upload.get_audio_file()
                if audio_file:
                    data = utils.get_audio_file_data(audio_file)
                    upload.bitrate = data["bitrate"]
                    upload.duration = data["length"]
                    upload.save(update_fields=["duration", "bitrate"])
                else:
                    self.stderr.write("[bitrate/length] no file found")
            except Exception as e:
                self.stderr.write(
                    "[bitrate/length] error with file #{}: {}".format(upload.pk, str(e))
                )

    def fix_file_size(self, dry_run, **kwargs):
        self.stdout.write("Fixing missing size...")
        matching = models.Upload.objects.filter(size__isnull=True)
        total = matching.count()
        self.stdout.write("[size] {} entries found with missing values".format(total))
        if dry_run:
            return
        for i, upload in enumerate(matching.only("size")):
            self.stdout.write(
                "[size] {}/{} fixing file #{}".format(i + 1, total, upload.pk)
            )

            try:
                upload.size = upload.get_file_size()
                upload.save(update_fields=["size"])
            except Exception as e:
                self.stderr.write(
                    "[size] error with file #{}: {}".format(upload.pk, str(e))
                )

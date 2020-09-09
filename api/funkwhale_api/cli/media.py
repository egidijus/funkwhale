import click

from django.core.cache import cache
from django.conf import settings
from django.core.files.storage import default_storage

from versatileimagefield.image_warmer import VersatileImageFieldWarmer
from versatileimagefield import settings as vif_settings

from funkwhale_api.common import utils as common_utils
from funkwhale_api.common.models import Attachment

from . import base


@base.cli.group()
def media():
    """Manage media files (avatars, covers, attachments…)"""
    pass


@media.command("generate-thumbnails")
@click.option("-d", "--delete", is_flag=True)
def generate_thumbnails(delete):
    """
    Generate thumbnails for all images (avatars, covers, etc.).

    This can take a long time and generate a lot of I/O depending of the size
    of your library.
    """
    click.echo("Deleting existing thumbnails…")
    if delete:
        try:
            # FileSystemStorage doesn't support deleting a non-empty directory
            # so we reimplemented a method to do so
            default_storage.force_delete("__sized__")
        except AttributeError:
            # backends doesn't support directory deletion
            pass
    MODELS = [
        (Attachment, "file", "attachment_square"),
    ]
    for model, attribute, key_set in MODELS:
        click.echo(
            "Generating thumbnails for {}.{}…".format(model._meta.label, attribute)
        )
        qs = model.objects.exclude(**{"{}__isnull".format(attribute): True})
        qs = qs.exclude(**{attribute: ""})
        cache_key = "*{}{}*".format(
            settings.MEDIA_URL, vif_settings.VERSATILEIMAGEFIELD_SIZED_DIRNAME
        )
        entries = cache.keys(cache_key)
        if entries:
            click.echo(
                "  Clearing {} cache entries: {}…".format(len(entries), cache_key)
            )
            for keys in common_utils.batch(iter(entries)):
                cache.delete_many(keys)
        warmer = VersatileImageFieldWarmer(
            instance_or_queryset=qs,
            rendition_key_set=key_set,
            image_attr=attribute,
            verbose=True,
        )
        click.echo("  Creating images")
        num_created, failed_to_create = warmer.warm()
        click.echo(
            "  {} created, {} in error".format(num_created, len(failed_to_create))
        )

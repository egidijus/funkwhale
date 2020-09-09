import uuid
import magic
import mimetypes

from django.contrib.postgres.fields import JSONField
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connections, models, transaction
from django.db.models import Lookup
from django.db.models.fields import Field
from django.db.models.sql.compiler import SQLCompiler
from django.dispatch import receiver
from django.utils import timezone
from django.urls import reverse

from versatileimagefield.fields import VersatileImageField
from versatileimagefield.image_warmer import VersatileImageFieldWarmer

from funkwhale_api.federation import utils as federation_utils

from . import utils
from . import validators


CONTENT_TEXT_MAX_LENGTH = 5000
CONTENT_TEXT_SUPPORTED_TYPES = [
    "text/html",
    "text/markdown",
    "text/plain",
]


@Field.register_lookup
class NotEqual(Lookup):
    lookup_name = "ne"

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return "%s <> %s" % (lhs, rhs), params


class NullsLastSQLCompiler(SQLCompiler):
    def get_order_by(self):
        result = super().get_order_by()
        if result and self.connection.vendor == "postgresql":
            return [
                (
                    expr,
                    (
                        sql + " NULLS LAST" if not sql.endswith(" NULLS LAST") else sql,
                        params,
                        is_ref,
                    ),
                )
                for (expr, (sql, params, is_ref)) in result
            ]
        return result


class NullsLastQuery(models.sql.query.Query):
    """Use a custom compiler to inject 'NULLS LAST' (for PostgreSQL)."""

    def get_compiler(self, using=None, connection=None):
        if using is None and connection is None:
            raise ValueError("Need either using or connection")
        if using:
            connection = connections[using]
        return NullsLastSQLCompiler(self, connection, using)


class NullsLastQuerySet(models.QuerySet):
    def __init__(self, model=None, query=None, using=None, hints=None):
        super().__init__(model, query, using, hints)
        self.query = query or NullsLastQuery(self.model)


class LocalFromFidQuerySet:
    def local(self, include=True):
        host = settings.FEDERATION_HOSTNAME
        query = models.Q(fid__startswith="http://{}/".format(host)) | models.Q(
            fid__startswith="https://{}/".format(host)
        )
        if include:
            return self.filter(query)
        else:
            return self.filter(~query)


class GenericTargetQuerySet(models.QuerySet):
    def get_for_target(self, target):
        content_type = ContentType.objects.get_for_model(target)
        return self.filter(target_content_type=content_type, target_id=target.pk)


class Mutation(models.Model):
    fid = models.URLField(unique=True, max_length=500, db_index=True)
    uuid = models.UUIDField(unique=True, db_index=True, default=uuid.uuid4)
    created_by = models.ForeignKey(
        "federation.Actor",
        related_name="created_mutations",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    approved_by = models.ForeignKey(
        "federation.Actor",
        related_name="approved_mutations",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    type = models.CharField(max_length=100, db_index=True)
    # None = no choice, True = approved, False = refused
    is_approved = models.NullBooleanField(default=None)

    # None = not applied, True = applied, False = failed
    is_applied = models.NullBooleanField(default=None)
    creation_date = models.DateTimeField(default=timezone.now, db_index=True)
    applied_date = models.DateTimeField(null=True, blank=True, db_index=True)
    summary = models.TextField(max_length=2000, null=True, blank=True)

    payload = JSONField(encoder=DjangoJSONEncoder)
    previous_state = JSONField(null=True, default=None, encoder=DjangoJSONEncoder)

    target_id = models.IntegerField(null=True)
    target_content_type = models.ForeignKey(
        ContentType,
        null=True,
        on_delete=models.CASCADE,
        related_name="targeting_mutations",
    )
    target = GenericForeignKey("target_content_type", "target_id")

    objects = GenericTargetQuerySet.as_manager()

    def get_federation_id(self):
        if self.fid:
            return self.fid

        return federation_utils.full_url(
            reverse("federation:edits-detail", kwargs={"uuid": self.uuid})
        )

    def save(self, **kwargs):
        if not self.pk and not self.fid:
            self.fid = self.get_federation_id()

        return super().save(**kwargs)

    @transaction.atomic
    def apply(self):
        from . import mutations

        if self.is_applied:
            raise ValueError("Mutation was already applied")

        previous_state = mutations.registry.apply(
            type=self.type, obj=self.target, payload=self.payload
        )
        self.previous_state = previous_state
        self.is_applied = True
        self.applied_date = timezone.now()
        self.save(update_fields=["is_applied", "applied_date", "previous_state"])
        return previous_state


def get_file_path(instance, filename):
    return utils.ChunkedPath("attachments")(instance, filename)


class AttachmentQuerySet(models.QuerySet):
    def attached(self, include=True):
        related_fields = [
            "covered_album",
            "mutation_attachment",
            "covered_track",
            "covered_artist",
            "iconed_actor",
        ]
        query = None
        for field in related_fields:
            field_query = ~models.Q(**{field: None})
            query = query | field_query if query else field_query

        if include is False:
            query = ~query

        return self.filter(query)

    def local(self, include=True):
        if include:
            return self.filter(actor__domain_id=settings.FEDERATION_HOSTNAME)
        else:
            return self.exclude(actor__domain_id=settings.FEDERATION_HOSTNAME)


class Attachment(models.Model):
    # Remote URL where the attachment can be fetched
    url = models.URLField(max_length=500, null=True, blank=True)
    uuid = models.UUIDField(unique=True, db_index=True, default=uuid.uuid4)
    # Actor associated with the attachment
    actor = models.ForeignKey(
        "federation.Actor",
        related_name="attachments",
        on_delete=models.CASCADE,
        null=True,
    )
    creation_date = models.DateTimeField(default=timezone.now)
    last_fetch_date = models.DateTimeField(null=True, blank=True)
    # File size
    size = models.IntegerField(null=True, blank=True)
    mimetype = models.CharField(null=True, blank=True, max_length=200)

    file = VersatileImageField(
        upload_to=get_file_path,
        max_length=255,
        validators=[
            validators.ImageDimensionsValidator(min_width=50, min_height=50),
            validators.FileValidator(
                allowed_extensions=["png", "jpg", "jpeg"], max_size=1024 * 1024 * 5,
            ),
        ],
    )

    objects = AttachmentQuerySet.as_manager()

    def save(self, **kwargs):
        if self.file and not self.size:
            self.size = self.file.size

        if self.file and not self.mimetype:
            self.mimetype = self.guess_mimetype()

        return super().save()

    @property
    def is_local(self):
        return federation_utils.is_local(self.fid)

    def guess_mimetype(self):
        f = self.file
        b = min(1000000, f.size)
        t = magic.from_buffer(f.read(b), mime=True)
        if not t.startswith("image/"):
            # failure, we try guessing by extension
            mt, _ = mimetypes.guess_type(f.name)
            if mt:
                t = mt
        return t

    @property
    def download_url_original(self):
        if self.file:
            return utils.media_url(self.file.url)
        proxy_url = reverse("api:v1:attachments-proxy", kwargs={"uuid": self.uuid})
        return federation_utils.full_url(proxy_url + "?next=original")

    @property
    def download_url_medium_square_crop(self):
        if self.file:
            return utils.media_url(self.file.crop["200x200"].url)
        proxy_url = reverse("api:v1:attachments-proxy", kwargs={"uuid": self.uuid})
        return federation_utils.full_url(proxy_url + "?next=medium_square_crop")

    @property
    def download_url_large_square_crop(self):
        if self.file:
            return utils.media_url(self.file.crop["600x600"].url)
        proxy_url = reverse("api:v1:attachments-proxy", kwargs={"uuid": self.uuid})
        return federation_utils.full_url(proxy_url + "?next=large_square_crop")


class MutationAttachment(models.Model):
    """
    When using attachments in mutations, we need to keep a reference to
    the attachment to ensure it is not pruned by common/tasks.py.

    This is what this model does.
    """

    attachment = models.OneToOneField(
        Attachment, related_name="mutation_attachment", on_delete=models.CASCADE
    )
    mutation = models.OneToOneField(
        Mutation, related_name="mutation_attachment", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("attachment", "mutation")


class Content(models.Model):
    """
    A text content that can be associated to other models, like a description, a summary, etc.
    """

    text = models.CharField(max_length=CONTENT_TEXT_MAX_LENGTH, blank=True, null=True)
    content_type = models.CharField(max_length=100)

    @property
    def rendered(self):
        from . import utils

        return utils.render_html(self.text, self.content_type)

    @property
    def as_plain_text(self):
        from . import utils

        return utils.render_plain_text(self.rendered)

    def truncate(self, length):
        text = self.as_plain_text
        truncated = text[:length]
        if len(truncated) < len(text):
            truncated += "…"

        return truncated


@receiver(models.signals.post_save, sender=Attachment)
def warm_attachment_thumbnails(sender, instance, **kwargs):
    if not instance.file or not settings.CREATE_IMAGE_THUMBNAILS:
        return
    warmer = VersatileImageFieldWarmer(
        instance_or_queryset=instance,
        rendition_key_set="attachment_square",
        image_attr="file",
    )
    num_created, failed_to_create = warmer.warm()


@receiver(models.signals.post_save, sender=Mutation)
def trigger_mutation_post_init(sender, instance, created, **kwargs):
    if not created:
        return

    from . import mutations

    try:
        conf = mutations.registry.get_conf(instance.type, instance.target)
    except mutations.ConfNotFound:
        return
    serializer = conf["serializer_class"]()
    try:
        handler = serializer.mutation_post_init
    except AttributeError:
        return
    handler(instance)


CONTENT_FKS = {
    "music.Track": ["description"],
    "music.Album": ["description"],
    "music.Artist": ["description"],
}


@receiver(models.signals.post_delete, sender=None)
def remove_attached_content(sender, instance, **kwargs):
    fk_fields = CONTENT_FKS.get(instance._meta.label, [])
    for field in fk_fields:
        if getattr(instance, "{}_id".format(field)):
            try:
                getattr(instance, field).delete()
            except Content.DoesNotExist:
                pass


class PluginConfiguration(models.Model):
    """
    Store plugin configuration in DB
    """

    code = models.CharField(max_length=100)
    user = models.ForeignKey(
        "users.User",
        related_name="plugins",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    conf = JSONField(null=True, blank=True)
    enabled = models.BooleanField(default=False)
    creation_date = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "code")

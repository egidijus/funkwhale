import uuid

from django.contrib.postgres.fields import JSONField
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.utils import timezone
from django.urls import reverse

from funkwhale_api.federation import utils as federation_utils


class MutationQuerySet(models.QuerySet):
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

    payload = JSONField()
    previous_state = JSONField(null=True, default=None)

    target_id = models.IntegerField(null=True)
    target_content_type = models.ForeignKey(
        ContentType,
        null=True,
        on_delete=models.CASCADE,
        related_name="targeting_mutations",
    )
    target = GenericForeignKey("target_content_type", "target_id")

    objects = MutationQuerySet.as_manager()

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

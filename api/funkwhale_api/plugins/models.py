from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.postgres.fields import JSONField

from django.db import models
from django.utils import timezone


class Plugin(models.Model):
    name = models.CharField(unique=True, max_length=70)
    creation_date = models.DateTimeField(default=timezone.now)
    is_enabled = models.BooleanField()
    config = JSONField(
        default=None, max_length=50000, encoder=DjangoJSONEncoder, blank=True, null=True
    )

    def __str__(self):
        return self.name


class UserPlugin(models.Model):
    plugin = models.ForeignKey(
        Plugin, related_name="user_plugins", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        "users.User", related_name="user_plugins", on_delete=models.CASCADE
    )
    creation_date = models.DateTimeField(default=timezone.now)
    is_enabled = models.BooleanField()

    config = JSONField(
        default=None, max_length=50000, encoder=DjangoJSONEncoder, blank=True, null=True
    )

    class Meta:
        unique_together = ("user", "plugin")

# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import datetime
import random
import string
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager as BaseUserManager
from django.contrib.postgres.fields import JSONField
from django.db import models, transaction
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from allauth.account.models import EmailAddress
from django_auth_ldap.backend import populate_user as ldap_populate_user
from oauth2_provider import models as oauth2_models
from oauth2_provider import validators as oauth2_validators
from versatileimagefield.fields import VersatileImageField

from funkwhale_api.common import fields, preferences
from funkwhale_api.common import utils as common_utils
from funkwhale_api.common import validators as common_validators
from funkwhale_api.federation import keys
from funkwhale_api.federation import models as federation_models
from funkwhale_api.federation import utils as federation_utils


def get_token(length=30):
    choices = string.ascii_lowercase + string.ascii_uppercase + "0123456789"
    return "".join(random.choice(choices) for i in range(length))


PERMISSIONS_CONFIGURATION = {
    "moderation": {
        "label": "Moderation",
        "help_text": "Block/mute/remove domains, users and content",
        "scopes": {
            "read:instance:policies",
            "write:instance:policies",
            "read:instance:accounts",
            "write:instance:accounts",
            "read:instance:domains",
            "write:instance:domains",
            "read:instance:reports",
            "write:instance:reports",
            "read:instance:requests",
            "write:instance:requests",
            "read:instance:notes",
            "write:instance:notes",
        },
    },
    "library": {
        "label": "Manage library",
        "help_text": "Manage library, delete files, tracks, artists, albums...",
        "scopes": {
            "read:instance:edits",
            "write:instance:edits",
            "read:instance:libraries",
            "write:instance:libraries",
        },
    },
    "settings": {
        "label": "Manage instance-level settings",
        "help_text": "",
        "scopes": {
            "read:instance:settings",
            "write:instance:settings",
            "read:instance:users",
            "write:instance:users",
            "read:instance:invitations",
            "write:instance:invitations",
        },
    },
}

PERMISSIONS = sorted(PERMISSIONS_CONFIGURATION.keys())


get_file_path = common_utils.ChunkedPath("users/avatars", preserve_file_name=False)


def get_default_instance_support_message_display_date():
    return timezone.now() + datetime.timedelta(
        days=settings.INSTANCE_SUPPORT_MESSAGE_DELAY
    )


def get_default_funkwhale_support_message_display_date():
    return timezone.now() + datetime.timedelta(
        days=settings.FUNKWHALE_SUPPORT_MESSAGE_DELAY
    )


class UserQuerySet(models.QuerySet):
    def for_auth(self):
        """Optimization to avoid additional queries during authentication"""
        qs = self.select_related("actor__domain")
        verified_emails = EmailAddress.objects.filter(
            user=models.OuterRef("id"), primary=True
        ).values("verified")[:1]
        subquery = models.Subquery(verified_emails)
        return qs.annotate(has_verified_primary_email=subquery).prefetch_related(
            "plugins"
        )


class UserManager(BaseUserManager):
    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)

    def get_by_natural_key(self, key):
        obj = BaseUserManager.get_by_natural_key(self.all().for_auth(), key)
        return obj


class User(AbstractUser):

    # First Name and Last Name do not cover name patterns
    # around the globe.
    name = models.CharField(_("Name of User"), blank=True, max_length=255)

    # updated on logout or password change, to invalidate JWT
    secret_key = models.UUIDField(default=uuid.uuid4, null=True)
    privacy_level = fields.get_privacy_field()

    # Unfortunately, Subsonic API assumes a MD5/password authentication
    # scheme, which is weak in terms of security, and not achievable
    # anyway since django use stronger schemes for storing passwords.
    # Users that want to use the subsonic API from external client
    # should set this token and use it as their password in such clients
    subsonic_api_token = models.CharField(blank=True, null=True, max_length=255)

    # permissions
    permission_moderation = models.BooleanField(
        PERMISSIONS_CONFIGURATION["moderation"]["label"],
        help_text=PERMISSIONS_CONFIGURATION["moderation"]["help_text"],
        default=False,
    )
    permission_library = models.BooleanField(
        PERMISSIONS_CONFIGURATION["library"]["label"],
        help_text=PERMISSIONS_CONFIGURATION["library"]["help_text"],
        default=False,
    )
    permission_settings = models.BooleanField(
        PERMISSIONS_CONFIGURATION["settings"]["label"],
        help_text=PERMISSIONS_CONFIGURATION["settings"]["help_text"],
        default=False,
    )

    last_activity = models.DateTimeField(default=None, null=True, blank=True)

    invitation = models.ForeignKey(
        "Invitation",
        related_name="users",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    avatar = VersatileImageField(
        upload_to=get_file_path,
        null=True,
        blank=True,
        max_length=150,
        validators=[
            common_validators.ImageDimensionsValidator(min_width=50, min_height=50),
            common_validators.FileValidator(
                allowed_extensions=["png", "jpg", "jpeg", "gif"],
                max_size=1024 * 1024 * 2,
            ),
        ],
    )
    actor = models.OneToOneField(
        "federation.Actor",
        related_name="user",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    upload_quota = models.PositiveIntegerField(null=True, blank=True)

    instance_support_message_display_date = models.DateTimeField(
        default=get_default_instance_support_message_display_date, null=True, blank=True
    )
    funkwhale_support_message_display_date = models.DateTimeField(
        default=get_default_funkwhale_support_message_display_date,
        null=True,
        blank=True,
    )
    settings = JSONField(default=None, null=True, blank=True, max_length=50000)

    objects = UserManager()

    def __str__(self):
        return self.username

    def get_permissions(self, defaults=None):
        defaults = defaults or preferences.get("users__default_permissions")
        perms = {}
        for p in PERMISSIONS:
            v = (
                self.is_superuser
                or getattr(self, "permission_{}".format(p))
                or p in defaults
            )
            perms[p] = v
        return perms

    @property
    def all_permissions(self):
        return self.get_permissions()

    @transaction.atomic
    def set_settings(self, **settings):
        u = self.__class__.objects.select_for_update().get(pk=self.pk)
        if not u.settings:
            u.settings = {}
        for key, value in settings.items():
            u.settings[key] = value
        u.save(update_fields=["settings"])
        self.settings = u.settings

    def has_permissions(self, *perms, **kwargs):
        operator = kwargs.pop("operator", "and")
        if operator not in ["and", "or"]:
            raise ValueError("Invalid operator {}".format(operator))
        permissions = self.get_permissions()
        checker = all if operator == "and" else any
        return checker([permissions[p] for p in perms])

    def get_absolute_url(self):
        return reverse("users:detail", kwargs={"username": self.username})

    def update_secret_key(self):
        self.secret_key = uuid.uuid4()
        return self.secret_key

    def update_subsonic_api_token(self):
        self.subsonic_api_token = get_token()
        return self.subsonic_api_token

    def set_password(self, raw_password):
        super().set_password(raw_password)
        self.update_secret_key()
        if self.subsonic_api_token:
            self.update_subsonic_api_token()

    def get_activity_url(self):
        return settings.FUNKWHALE_URL + "/@{}".format(self.username)

    def record_activity(self):
        """
        Simply update the last_activity field if current value is too old
        than a threshold. This is useful to keep a track of inactive accounts.
        """
        current = self.last_activity
        delay = 60 * 15  # fifteen minutes
        now = timezone.now()

        if current is None or current < now - datetime.timedelta(seconds=delay):
            self.last_activity = now
            self.save(update_fields=["last_activity"])

    def create_actor(self, **kwargs):
        self.actor = create_actor(self, **kwargs)
        self.save(update_fields=["actor"])
        return self.actor

    def get_upload_quota(self):
        return (
            self.upload_quota
            if self.upload_quota is not None
            else preferences.get("users__upload_quota")
        )

    def get_quota_status(self):
        data = self.actor.get_current_usage()
        max_ = self.get_upload_quota()
        return {
            "max": max_,
            "remaining": max(max_ - (data["total"] / 1000 / 1000), 0),
            "current": data["total"] / 1000 / 1000,
            "draft": data["draft"] / 1000 / 1000,
            "skipped": data["skipped"] / 1000 / 1000,
            "pending": data["pending"] / 1000 / 1000,
            "finished": data["finished"] / 1000 / 1000,
            "errored": data["errored"] / 1000 / 1000,
        }

    def get_channels_groups(self):
        groups = ["imports", "inbox"]
        groups = ["user.{}.{}".format(self.pk, g) for g in groups]

        for permission, value in self.all_permissions.items():
            if value:
                groups.append("admin.{}".format(permission))

        return groups

    def full_username(self):
        return "{}@{}".format(self.username, settings.FEDERATION_HOSTNAME)

    def get_avatar(self):
        if not self.actor:
            return
        return self.actor.attachment_icon


def generate_code(length=10):
    return "".join(
        random.SystemRandom().choice(string.ascii_uppercase) for _ in range(length)
    )


class InvitationQuerySet(models.QuerySet):
    def open(self, include=True):
        now = timezone.now()
        qs = self.annotate(_users=models.Count("users"))
        query = models.Q(_users=0, expiration_date__gt=now)
        if include:
            return qs.filter(query)
        return qs.exclude(query)


class Invitation(models.Model):
    creation_date = models.DateTimeField(default=timezone.now)
    expiration_date = models.DateTimeField()
    owner = models.ForeignKey(
        User, related_name="invitations", on_delete=models.CASCADE
    )
    code = models.CharField(max_length=50, unique=True)

    objects = InvitationQuerySet.as_manager()

    def save(self, **kwargs):
        if not self.code:
            self.code = generate_code()
        if not self.expiration_date:
            self.expiration_date = self.creation_date + datetime.timedelta(
                days=settings.USERS_INVITATION_EXPIRATION_DAYS
            )

        return super().save(**kwargs)


class Application(oauth2_models.AbstractApplication):
    scope = models.TextField(blank=True)
    token = models.CharField(max_length=50, blank=True, null=True, unique=True)

    @property
    def normalized_scopes(self):
        from .oauth import permissions

        raw_scopes = set(self.scope.split(" ") if self.scope else [])
        return permissions.normalize(*raw_scopes)


# oob schemes are not supported yet in oauth toolkit
# (https://github.com/jazzband/django-oauth-toolkit/issues/235)
# so in the meantime, we override their validation to add support
OOB_SCHEMES = ["urn:ietf:wg:oauth:2.0:oob", "urn:ietf:wg:oauth:2.0:oob:auto"]


class CustomRedirectURIValidator(oauth2_validators.RedirectURIValidator):
    def __call__(self, value):
        if value in OOB_SCHEMES:
            return value
        return super().__call__(value)


oauth2_models.RedirectURIValidator = CustomRedirectURIValidator


class Grant(oauth2_models.AbstractGrant):
    pass


class AccessToken(oauth2_models.AbstractAccessToken):
    pass


class RefreshToken(oauth2_models.AbstractRefreshToken):
    pass


def get_actor_data(username, **kwargs):
    slugified_username = federation_utils.slugify_username(username)
    domain = kwargs.get("domain")
    if not domain:
        domain = federation_models.Domain.objects.get_or_create(
            name=settings.FEDERATION_HOSTNAME
        )[0]
    return {
        "preferred_username": slugified_username,
        "domain": domain,
        "type": "Person",
        "name": kwargs.get("name", username),
        "summary": kwargs.get("summary"),
        "manually_approves_followers": False,
        "fid": federation_utils.full_url(
            reverse(
                "federation:actors-detail",
                kwargs={"preferred_username": slugified_username},
            )
        ),
        "shared_inbox_url": federation_models.get_shared_inbox_url(),
        "inbox_url": federation_utils.full_url(
            reverse(
                "federation:actors-inbox",
                kwargs={"preferred_username": slugified_username},
            )
        ),
        "outbox_url": federation_utils.full_url(
            reverse(
                "federation:actors-outbox",
                kwargs={"preferred_username": slugified_username},
            )
        ),
        "followers_url": federation_utils.full_url(
            reverse(
                "federation:actors-followers",
                kwargs={"preferred_username": slugified_username},
            )
        ),
        "following_url": federation_utils.full_url(
            reverse(
                "federation:actors-following",
                kwargs={"preferred_username": slugified_username},
            )
        ),
    }


def create_actor(user, **kwargs):
    args = get_actor_data(user.username)
    args.update(kwargs)
    private, public = keys.get_key_pair()
    args["private_key"] = private.decode("utf-8")
    args["public_key"] = public.decode("utf-8")

    return federation_models.Actor.objects.create(user=user, **args)


@receiver(ldap_populate_user)
def init_ldap_user(sender, user, ldap_user, **kwargs):
    if not user.actor:
        user.actor = create_actor(user)

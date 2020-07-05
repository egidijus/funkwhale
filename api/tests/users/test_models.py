import datetime
import pytest

from django.urls import reverse

from funkwhale_api.users import models
from funkwhale_api.federation import utils as federation_utils


def test__str__(factories):
    user = factories["users.User"](username="hello")
    assert user.__str__() == "hello"


def test_changing_password_updates_subsonic_api_token_no_token(factories):
    user = factories["users.User"](subsonic_api_token=None)
    user.set_password("new")
    assert user.subsonic_api_token is None


def test_changing_password_updates_subsonic_api_token(factories):
    user = factories["users.User"](subsonic_api_token="test")
    user.set_password("new")

    assert user.subsonic_api_token is not None
    assert user.subsonic_api_token != "test"


def test_get_permissions_superuser(factories):
    user = factories["users.User"](is_superuser=True)

    perms = user.get_permissions()
    for p in models.PERMISSIONS:
        assert perms[p] is True


def test_get_permissions_regular(factories):
    user = factories["users.User"](permission_library=True)

    perms = user.get_permissions()
    for p in models.PERMISSIONS:
        if p == "library":
            assert perms[p] is True
        else:
            assert perms[p] is False


def test_get_permissions_default(factories, preferences):
    preferences["users__default_permissions"] = ["library", "moderation"]
    user = factories["users.User"]()

    perms = user.get_permissions()
    assert perms["moderation"] is True
    assert perms["library"] is True
    assert perms["settings"] is False


@pytest.mark.parametrize(
    "args,perms,expected",
    [
        ({"is_superuser": True}, ["moderation", "library"], True),
        ({"is_superuser": False}, ["moderation"], False),
        ({"permission_library": True}, ["library"], True),
        ({"permission_library": True}, ["library", "moderation"], False),
    ],
)
def test_has_permissions_and(args, perms, expected, factories):
    user = factories["users.User"](**args)
    assert user.has_permissions(*perms, operator="and") is expected


@pytest.mark.parametrize(
    "args,perms,expected",
    [
        ({"is_superuser": True}, ["moderation", "library"], True),
        ({"is_superuser": False}, ["moderation"], False),
        ({"permission_library": True}, ["library", "moderation"], True),
        ({"permission_library": True}, ["moderation"], False),
    ],
)
def test_has_permissions_or(args, perms, expected, factories):
    user = factories["users.User"](**args)
    assert user.has_permissions(*perms, operator="or") is expected


def test_record_activity(factories, now):
    user = factories["users.User"]()
    assert user.last_activity is None

    user.record_activity()

    assert user.last_activity == now


def test_record_activity_does_nothing_if_already(factories, now, mocker):
    user = factories["users.User"](last_activity=now)
    save = mocker.patch("funkwhale_api.users.models.User.save")
    user.record_activity()

    save.assert_not_called()


def test_invitation_generates_random_code_on_save(factories):
    invitation = factories["users.Invitation"]()
    assert len(invitation.code) >= 6


def test_invitation_expires_after_delay(factories, settings):
    delay = settings.USERS_INVITATION_EXPIRATION_DAYS
    invitation = factories["users.Invitation"]()
    assert invitation.expiration_date == (
        invitation.creation_date + datetime.timedelta(days=delay)
    )


def test_can_filter_open_invitations(factories):
    okay = factories["users.Invitation"]()
    factories["users.Invitation"](expired=True)
    factories["users.User"](invited=True)

    assert models.Invitation.objects.count() == 3
    assert list(models.Invitation.objects.open()) == [okay]


def test_can_filter_closed_invitations(factories):
    factories["users.Invitation"]()
    expired = factories["users.Invitation"](expired=True)
    used = factories["users.User"](invited=True).invitation

    assert models.Invitation.objects.count() == 3
    assert list(models.Invitation.objects.order_by("id").open(False)) == [expired, used]


def test_creating_actor_from_user(factories, settings):
    user = factories["users.User"](username="Hello M. world")
    actor = models.create_actor(user)

    assert actor.preferred_username == "Hello_M_world"  # slugified
    assert actor.domain.pk == settings.FEDERATION_HOSTNAME
    assert actor.type == "Person"
    assert actor.name == user.username
    assert actor.manually_approves_followers is False
    assert actor.fid == federation_utils.full_url(
        reverse(
            "federation:actors-detail",
            kwargs={"preferred_username": actor.preferred_username},
        )
    )
    assert actor.shared_inbox_url == federation_utils.full_url(
        reverse("federation:shared-inbox")
    )
    assert actor.inbox_url == federation_utils.full_url(
        reverse(
            "federation:actors-inbox",
            kwargs={"preferred_username": actor.preferred_username},
        )
    )
    assert actor.outbox_url == federation_utils.full_url(
        reverse(
            "federation:actors-outbox",
            kwargs={"preferred_username": actor.preferred_username},
        )
    )
    assert actor.followers_url == federation_utils.full_url(
        reverse(
            "federation:actors-followers",
            kwargs={"preferred_username": actor.preferred_username},
        )
    )
    assert actor.following_url == federation_utils.full_url(
        reverse(
            "federation:actors-following",
            kwargs={"preferred_username": actor.preferred_username},
        )
    )


def test_get_channels_groups(factories):
    user = factories["users.User"](permission_library=True)

    assert user.get_channels_groups() == [
        "user.{}.imports".format(user.pk),
        "user.{}.inbox".format(user.pk),
        "admin.library",
    ]


@pytest.mark.parametrize(
    "default_quota, user_quota, expected",
    [(1000, None, 1000), (1000, 42, 42), (1000, 0, 0)],
)
def test_user_quota_set_on_user(
    default_quota, user_quota, expected, factories, preferences
):
    preferences["users__upload_quota"] = default_quota

    user = factories["users.User"](upload_quota=user_quota)
    assert user.get_upload_quota() == expected


def test_user_get_quota_status(factories, preferences, mocker):
    user = factories["users.User"](upload_quota=66, with_actor=True)
    mocker.patch(
        "funkwhale_api.federation.models.Actor.get_current_usage",
        return_value={
            "total": 15 * 1000 * 1000,
            "pending": 1 * 1000 * 1000,
            "skipped": 2 * 1000 * 1000,
            "errored": 3 * 1000 * 1000,
            "finished": 4 * 1000 * 1000,
            "draft": 5 * 1000 * 1000,
        },
    )
    assert user.get_quota_status() == {
        "max": 66,
        "remaining": 51,
        "current": 15,
        "pending": 1,
        "skipped": 2,
        "errored": 3,
        "finished": 4,
        "draft": 5,
    }


@pytest.mark.parametrize(
    "setting_name, field",
    [
        ("INSTANCE_SUPPORT_MESSAGE_DELAY", "instance_support_message_display_date"),
        ("FUNKWHALE_SUPPORT_MESSAGE_DELAY", "funkwhale_support_message_display_date"),
    ],
)
def test_creating_user_set_support_display_date(
    setting_name, field, settings, factories, now
):
    setattr(settings, setting_name, 66)  # display message every 66 days
    expected = now + datetime.timedelta(days=66)
    user = factories["users.User"]()

    assert getattr(user, field) == expected


def test_get_by_natural_key_annotates_primary_email_verified_no_email(factories):
    user = factories["users.User"]()
    user = models.User.objects.get_by_natural_key(user.username)

    assert user.has_verified_primary_email is None


def test_get_by_natural_key_annotates_primary_email_verified_true(factories):
    user = factories["users.User"](verified_email=True)
    user = models.User.objects.get_by_natural_key(user.username)

    assert user.has_verified_primary_email is True


def test_get_by_natural_key_annotates_primary_email_verified_false(factories):
    user = factories["users.User"](verified_email=False)
    user = models.User.objects.get_by_natural_key(user.username)

    assert user.has_verified_primary_email is False


def test_set_settings(factories):
    user = factories["users.User"]()
    assert user.settings is None

    user.set_settings(foo="bar", hello="world")

    user.refresh_from_db()
    assert user.settings == {
        "foo": "bar",
        "hello": "world",
    }

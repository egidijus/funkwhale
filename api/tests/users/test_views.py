import pytest
from django.urls import reverse

from django.test import Client

from funkwhale_api.common import serializers as common_serializers
from funkwhale_api.common import utils as common_utils
from funkwhale_api.moderation import tasks as moderation_tasks
from funkwhale_api.users.models import User


def test_can_create_user_via_api(preferences, api_client, db):
    url = reverse("rest_register")
    data = {
        "username": "test1",
        "email": "test1@test.com",
        "password1": "thisismypassword",
        "password2": "thisismypassword",
    }
    preferences["users__registration_enabled"] = True
    response = api_client.post(url, data)
    assert response.status_code == 201

    u = User.objects.get(email="test1@test.com")
    assert u.username == "test1"


@pytest.mark.parametrize("username", ["wrong.name", "wrong-name", "éaeu", "wrong name"])
def test_username_only_accepts_letters_and_underscores(
    username, preferences, api_client, db
):
    url = reverse("rest_register")
    data = {
        "username": username,
        "email": "test1@test.com",
        "password1": "testtest",
        "password2": "testtest",
    }
    preferences["users__registration_enabled"] = True
    response = api_client.post(url, data)
    assert response.status_code == 400


def test_can_restrict_usernames(settings, preferences, db, api_client):
    url = reverse("rest_register")
    preferences["users__registration_enabled"] = True
    settings.ACCOUNT_USERNAME_BLACKLIST = ["funkwhale"]
    data = {
        "username": "funkwhale",
        "email": "contact@funkwhale.io",
        "password1": "testtest",
        "password2": "testtest",
    }

    response = api_client.post(url, data)

    assert response.status_code == 400
    assert "username" in response.data


def test_can_disable_registration_view(preferences, api_client, db):
    url = reverse("rest_register")
    data = {
        "username": "test1",
        "email": "test1@test.com",
        "password1": "testtest",
        "password2": "testtest",
    }
    preferences["users__registration_enabled"] = False
    response = api_client.post(url, data)
    assert response.status_code == 403


def test_can_signup_with_invitation(preferences, factories, api_client):
    url = reverse("rest_register")
    invitation = factories["users.Invitation"](code="Hello")
    data = {
        "username": "test1",
        "email": "test1@test.com",
        "password1": "thisismypassword",
        "password2": "thisismypassword",
        "invitation": "hello",
    }
    preferences["users__registration_enabled"] = False
    response = api_client.post(url, data)
    assert response.status_code == 201
    u = User.objects.get(email="test1@test.com")
    assert u.username == "test1"
    assert u.invitation == invitation


def test_can_signup_with_invitation_invalid(preferences, factories, api_client):
    url = reverse("rest_register")
    factories["users.Invitation"](code="hello")
    data = {
        "username": "test1",
        "email": "test1@test.com",
        "password1": "testtest",
        "password2": "testtest",
        "invitation": "nope",
    }
    response = api_client.post(url, data)
    assert response.status_code == 400
    assert "invitation" in response.data


def test_can_fetch_data_from_api(api_client, factories):
    url = reverse("api:v1:users:users-me")
    response = api_client.get(url)
    # login required
    assert response.status_code == 401

    user = factories["users.User"](permission_library=True, with_actor=True)
    summary = {"content_type": "text/plain", "text": "Hello"}
    summary_obj = common_utils.attach_content(user.actor, "summary_obj", summary)
    avatar = factories["common.Attachment"]()
    user.actor.attachment_icon = avatar
    user.actor.save()
    api_client.login(username=user.username, password="test")
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.data["username"] == user.username
    assert response.data["is_staff"] == user.is_staff
    assert response.data["is_superuser"] == user.is_superuser
    assert response.data["email"] == user.email
    assert response.data["name"] == user.name
    assert response.data["permissions"] == user.get_permissions()
    assert (
        response.data["avatar"] == common_serializers.AttachmentSerializer(avatar).data
    )
    assert (
        response.data["summary"]
        == common_serializers.ContentSerializer(summary_obj).data
    )


def test_can_get_token_via_api(api_client, factories):
    user = factories["users.User"]()
    url = reverse("api:v1:token")
    payload = {"username": user.username, "password": "test"}

    response = api_client.post(url, payload)
    assert response.status_code == 200
    assert "token" in response.data


def test_can_get_token_via_api_inactive(api_client, factories):
    user = factories["users.User"](is_active=False)
    url = reverse("api:v1:token")
    payload = {"username": user.username, "password": "test"}

    response = api_client.post(url, payload)
    assert response.status_code == 400


def test_can_refresh_token_via_api(api_client, factories, mocker):
    # first, we get a token
    user = factories["users.User"]()
    url = reverse("api:v1:token")
    payload = {"username": user.username, "password": "test"}

    response = api_client.post(url, payload)
    assert response.status_code == 200

    token = response.data["token"]
    url = reverse("api:v1:token_refresh")
    response = api_client.post(url, {"token": token})

    assert response.status_code == 200
    assert "token" in response.data


def test_changing_password_updates_secret_key(logged_in_api_client):
    user = logged_in_api_client.user
    password = user.password
    secret_key = user.secret_key
    payload = {
        "old_password": "test",
        "new_password1": "thisismypassword",
        "new_password2": "thisismypassword",
    }
    url = reverse("change_password")

    response = logged_in_api_client.post(url, payload)

    assert response.status_code == 200
    user.refresh_from_db()

    assert user.secret_key != secret_key
    assert user.password != password


def test_can_request_password_reset(
    factories, preferences, settings, api_client, mailoutbox
):
    user = factories["users.User"]()
    payload = {"email": user.email}
    url = reverse("rest_password_reset")
    preferences["instance__name"] = "Hello world"

    response = api_client.post(url, payload)
    assert response.status_code == 200

    confirmation_message = mailoutbox[-1]
    assert "Hello world" in confirmation_message.body
    assert settings.FUNKWHALE_HOSTNAME in confirmation_message.body


def test_user_can_patch_his_own_settings(logged_in_api_client):
    user = logged_in_api_client.user
    payload = {"privacy_level": "me"}
    url = reverse("api:v1:users:users-detail", kwargs={"username": user.username})

    response = logged_in_api_client.patch(url, payload)

    assert response.status_code == 200
    user.refresh_from_db()

    assert user.privacy_level == "me"


def test_user_can_patch_description(logged_in_api_client):
    user = logged_in_api_client.user
    payload = {"summary": {"content_type": "text/markdown", "text": "hello"}}
    url = reverse("api:v1:users:users-detail", kwargs={"username": user.username})

    response = logged_in_api_client.patch(url, payload, format="json")

    assert response.status_code == 200
    user.refresh_from_db()

    assert user.actor.summary_obj.content_type == payload["summary"]["content_type"]
    assert user.actor.summary_obj.text == payload["summary"]["text"]


def test_user_can_request_new_subsonic_token(logged_in_api_client):
    user = logged_in_api_client.user
    user.subsonic_api_token = "test"
    user.save()

    url = reverse(
        "api:v1:users:users-subsonic-token", kwargs={"username": user.username}
    )

    response = logged_in_api_client.post(url)

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.subsonic_api_token != "test"
    assert user.subsonic_api_token is not None
    assert response.data == {"subsonic_api_token": user.subsonic_api_token}


def test_user_can_get_subsonic_token(logged_in_api_client):
    user = logged_in_api_client.user
    user.subsonic_api_token = "test"
    user.save()

    url = reverse(
        "api:v1:users:users-subsonic-token", kwargs={"username": user.username}
    )

    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert response.data == {"subsonic_api_token": "test"}


def test_user_can_request_new_subsonic_token_uncommon_username(logged_in_api_client):
    user = logged_in_api_client.user
    user.username = "firstname.lastname"
    user.subsonic_api_token = "test"
    user.save()

    url = reverse(
        "api:v1:users:users-subsonic-token", kwargs={"username": user.username}
    )

    response = logged_in_api_client.post(url)

    assert response.status_code == 200


def test_user_can_delete_subsonic_token(logged_in_api_client):
    user = logged_in_api_client.user
    user.subsonic_api_token = "test"
    user.save()

    url = reverse(
        "api:v1:users:users-subsonic-token", kwargs={"username": user.username}
    )

    response = logged_in_api_client.delete(url)

    assert response.status_code == 204
    user.refresh_from_db()
    assert user.subsonic_api_token is None


@pytest.mark.parametrize("method", ["put", "patch"])
def test_user_cannot_patch_another_user(method, logged_in_api_client, factories):
    user = factories["users.User"]()
    payload = {"privacy_level": "me"}
    url = reverse("api:v1:users:users-detail", kwargs={"username": user.username})

    handler = getattr(logged_in_api_client, method)
    response = handler(url, payload)

    assert response.status_code == 403


def test_user_can_patch_their_own_avatar(logged_in_api_client, factories):
    user = logged_in_api_client.user
    actor = user.create_actor()
    attachment = factories["common.Attachment"](actor=actor)
    url = reverse("api:v1:users:users-detail", kwargs={"username": user.username})
    payload = {"avatar": attachment.uuid}
    response = logged_in_api_client.patch(url, payload)

    assert response.status_code == 200
    user.refresh_from_db()

    assert user.actor.attachment_icon == attachment
    assert "avatar" in response.data


def test_creating_user_creates_actor_as_well(
    api_client, factories, mocker, preferences
):
    actor = factories["federation.Actor"]()
    url = reverse("rest_register")
    data = {
        "username": "test1",
        "email": "test1@test.com",
        "password1": "thisismypassword",
        "password2": "thisismypassword",
    }
    preferences["users__registration_enabled"] = True
    mocker.patch("funkwhale_api.users.models.create_actor", return_value=actor)
    response = api_client.post(url, data)

    assert response.status_code == 201

    user = User.objects.get(username="test1")

    assert user.actor == actor


def test_creating_user_sends_confirmation_email(
    api_client, db, settings, preferences, mailoutbox
):
    url = reverse("rest_register")
    data = {
        "username": "test1",
        "email": "test1@test.com",
        "password1": "thisismypassword",
        "password2": "thisismypassword",
    }
    preferences["users__registration_enabled"] = True
    preferences["instance__name"] = "Hello world"
    response = api_client.post(url, data)

    assert response.status_code == 201

    confirmation_message = mailoutbox[-1]
    assert "Hello world" in confirmation_message.body
    assert settings.FUNKWHALE_HOSTNAME in confirmation_message.body


def test_user_account_deletion_requires_valid_password(logged_in_api_client):
    user = logged_in_api_client.user
    user.set_password("mypassword")
    url = reverse("api:v1:users:users-me")
    payload = {"password": "invalid", "confirm": True}
    response = logged_in_api_client.delete(url, payload)

    assert response.status_code == 400


def test_user_account_deletion_requires_confirmation(logged_in_api_client):
    user = logged_in_api_client.user
    user.set_password("mypassword")
    url = reverse("api:v1:users:users-me")
    payload = {"password": "mypassword", "confirm": False}
    response = logged_in_api_client.delete(url, payload)

    assert response.status_code == 400


def test_user_account_deletion_triggers_delete_account(logged_in_api_client, mocker):
    user = logged_in_api_client.user
    user.set_password("mypassword")
    url = reverse("api:v1:users:users-me")
    payload = {"password": "mypassword", "confirm": True}
    delete_account = mocker.patch("funkwhale_api.users.tasks.delete_account.delay")
    response = logged_in_api_client.delete(url, payload)

    assert response.status_code == 204
    delete_account.assert_called_once_with(user_id=user.pk)


def test_username_with_existing_local_account_are_invalid(
    settings, preferences, factories, api_client
):
    actor = factories["users.User"]().create_actor()
    user = actor.user
    user.delete()
    url = reverse("rest_register")
    preferences["users__registration_enabled"] = True
    settings.ACCOUNT_USERNAME_BLACKLIST = []
    data = {
        "username": user.username,
        "email": "contact@funkwhale.io",
        "password1": "testtest",
        "password2": "testtest",
    }

    response = api_client.post(url, data)

    assert response.status_code == 400
    assert "username" in response.data


def test_signup_with_approval_enabled(
    preferences, factories, api_client, mocker, mailoutbox, settings
):
    url = reverse("rest_register")
    data = {
        "username": "test1",
        "email": "test1@test.com",
        "password1": "thisismypassword",
        "password2": "thisismypassword",
        "request_fields": {"field1": "Value 1", "field2": "Value 2", "noop": "Noop"},
    }
    preferences["users__registration_enabled"] = True
    preferences["moderation__signup_approval_enabled"] = True
    preferences["moderation__signup_form_customization"] = {
        "fields": [
            {"label": "field1", "input_type": "short_text"},
            {"label": "field2", "input_type": "short_text"},
        ]
    }
    on_commit = mocker.patch("funkwhale_api.common.utils.on_commit")
    response = api_client.post(url, data, format="json")
    assert response.status_code == 201
    u = User.objects.get(email="test1@test.com")
    assert u.username == "test1"
    assert u.is_active is False
    user_request = u.actor.requests.latest("id")
    assert user_request.type == "signup"
    assert user_request.status == "pending"
    assert user_request.metadata == {
        "field1": "Value 1",
        "field2": "Value 2",
    }

    on_commit.assert_any_call(
        moderation_tasks.user_request_handle.delay,
        user_request_id=user_request.pk,
        new_status="pending",
    )

    confirmation_message = mailoutbox[-1]
    assert "confirm" in confirmation_message.body
    assert settings.FUNKWHALE_HOSTNAME in confirmation_message.body


def test_signup_with_approval_enabled_validation_error(
    preferences, factories, api_client
):
    url = reverse("rest_register")
    data = {
        "username": "test1",
        "email": "test1@test.com",
        "password1": "thisismypassword",
        "password2": "thisismypassword",
        "request_fields": {"field1": "Value 1"},
    }
    preferences["users__registration_enabled"] = True
    preferences["moderation__signup_approval_enabled"] = True
    preferences["moderation__signup_form_customization"] = {
        "fields": [
            {"label": "field1", "input_type": "short_text"},
            {"label": "field2", "input_type": "short_text"},
        ]
    }
    response = api_client.post(url, data, format="json")
    assert response.status_code == 400


def test_user_login_jwt(factories, api_client):
    user = factories["users.User"]()
    data = {
        "username": user.username,
        "password": "test",
    }
    url = reverse("api:v1:token")
    response = api_client.post(url, data)
    assert response.status_code == 200


@pytest.mark.parametrize(
    "setting_value, verified_email, expected_status_code",
    [
        ("mandatory", False, 400),
        ("mandatory", True, 200),
        ("optional", False, 200),
        ("optional", True, 200),
    ],
)
def test_user_login_jwt_honor_email_verification(
    setting_value, verified_email, expected_status_code, settings, factories, api_client
):
    settings.ACCOUNT_EMAIL_VERIFICATION = setting_value
    user = factories["users.User"](verified_email=verified_email)
    data = {
        "username": user.username,
        "password": "test",
    }
    url = reverse("api:v1:token")
    response = api_client.post(url, data)
    assert response.status_code == expected_status_code


def test_login_via_api(api_client, factories):
    user = factories["users.User"]()
    url = reverse("api:v1:users:login")
    payload = {"username": user.username, "password": "test"}

    response = api_client.post(url, payload)
    assert response.status_code == 200
    assert api_client.session["_auth_user_id"] == str(user.pk)


def test_login_via_api_inactive(api_client, factories):
    user = factories["users.User"](is_active=False)
    url = reverse("api:v1:users:login")
    payload = {"username": user.username, "password": "test"}

    response = api_client.post(url, payload)
    assert response.status_code == 400


def test_login_via_api_no_csrf(factories):
    user = factories["users.User"]()
    url = reverse("api:v1:users:login")
    payload = {"username": user.username, "password": "test"}
    api_client = Client(enforce_csrf_checks=True)
    response = api_client.post(url, payload)
    assert response.status_code == 403


def test_logout(api_client, factories, mocker):
    auth_logout = mocker.patch("django.contrib.auth.logout")
    url = reverse("api:v1:users:logout")
    response = api_client.post(url)
    assert response.status_code == 200
    assert auth_logout.call_count == 1


def test_update_settings(logged_in_api_client, factories):
    logged_in_api_client.user.set_settings(foo="bar")
    url = reverse("api:v1:users:users-settings")
    payload = {"theme": "dark"}

    response = logged_in_api_client.post(url, payload, format="json")
    assert response.status_code == 200
    logged_in_api_client.user.refresh_from_db()

    assert logged_in_api_client.user.settings == {"foo": "bar", "theme": "dark"}


def test_user_change_email_requires_valid_password(logged_in_api_client):
    url = reverse("api:v1:users:users-change-email")
    payload = {"password": "invalid", "email": "test@new.email"}
    response = logged_in_api_client.post(url, payload)

    assert response.status_code == 400


def test_user_change_email(logged_in_api_client, mocker, mailoutbox):
    user = logged_in_api_client.user
    user.set_password("mypassword")
    url = reverse("api:v1:users:users-change-email")
    payload = {"password": "mypassword", "email": "test@new.email"}
    response = logged_in_api_client.post(url, payload)

    address = user.emailaddress_set.latest("id")

    assert address.email == payload["email"]
    assert address.verified is False
    assert response.status_code == 204
    assert len(mailoutbox) == 1

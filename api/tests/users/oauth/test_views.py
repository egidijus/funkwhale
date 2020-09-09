import json
import pytest

from django.urls import reverse

from funkwhale_api.users import models
from funkwhale_api.users.oauth import serializers


def test_apps_post(api_client, db):
    url = reverse("api:v1:oauth:apps-list")
    data = {
        "name": "Test app",
        "redirect_uris": "http://test.app",
        "scopes": "read write:profile",
    }
    response = api_client.post(url, data)

    assert response.status_code == 201

    app = models.Application.objects.get(name=data["name"])

    assert app.client_type == models.Application.CLIENT_CONFIDENTIAL
    assert app.authorization_grant_type == models.Application.GRANT_AUTHORIZATION_CODE
    assert app.redirect_uris == data["redirect_uris"]
    assert response.data == serializers.CreateApplicationSerializer(app).data
    assert app.scope == "read write:profile"
    assert app.user is None


def test_apps_post_logged_in_user(logged_in_api_client, db):
    url = reverse("api:v1:oauth:apps-list")
    data = {
        "name": "Test app",
        "redirect_uris": "http://test.app",
        "scopes": "read write:profile",
    }
    response = logged_in_api_client.post(url, data)

    assert response.status_code == 201

    app = models.Application.objects.get(name=data["name"])

    assert app.client_type == models.Application.CLIENT_CONFIDENTIAL
    assert app.authorization_grant_type == models.Application.GRANT_AUTHORIZATION_CODE
    assert app.redirect_uris == data["redirect_uris"]
    assert response.data == serializers.CreateApplicationSerializer(app).data
    assert app.scope == "read write:profile"
    assert app.user == logged_in_api_client.user
    assert app.token is not None
    assert response.data["token"] == app.token


def test_apps_list_anonymous(api_client, db):
    url = reverse("api:v1:oauth:apps-list")
    response = api_client.get(url)

    assert response.status_code == 401


def test_apps_list_logged_in(factories, logged_in_api_client, db):
    app = factories["users.Application"](user=logged_in_api_client.user)
    factories["users.Application"]()
    url = reverse("api:v1:oauth:apps-list")
    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert response.data["results"] == [serializers.ApplicationSerializer(app).data]


def test_apps_delete_not_owner(factories, logged_in_api_client, db):
    app = factories["users.Application"]()
    url = reverse("api:v1:oauth:apps-detail", kwargs={"client_id": app.client_id})
    response = logged_in_api_client.delete(url)

    assert response.status_code == 404


def test_apps_delete_owner(factories, logged_in_api_client, db):
    app = factories["users.Application"](user=logged_in_api_client.user)
    url = reverse("api:v1:oauth:apps-detail", kwargs={"client_id": app.client_id})
    response = logged_in_api_client.delete(url)

    assert response.status_code == 204

    with pytest.raises(app.DoesNotExist):
        app.refresh_from_db()


def test_apps_update_not_owner(factories, logged_in_api_client, db):
    app = factories["users.Application"]()
    url = reverse("api:v1:oauth:apps-detail", kwargs={"client_id": app.client_id})
    response = logged_in_api_client.patch(url, {"name": "Hello"})

    assert response.status_code == 404


def test_apps_update_owner(factories, logged_in_api_client, db):
    app = factories["users.Application"](user=logged_in_api_client.user)
    url = reverse("api:v1:oauth:apps-detail", kwargs={"client_id": app.client_id})
    response = logged_in_api_client.patch(url, {"name": "Hello"})

    assert response.status_code == 200
    app.refresh_from_db()

    assert app.name == "Hello"


def test_apps_get(preferences, logged_in_api_client, factories):
    app = factories["users.Application"]()
    url = reverse("api:v1:oauth:apps-detail", kwargs={"client_id": app.client_id})
    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert response.data == serializers.ApplicationSerializer(app).data


def test_apps_get_owner(preferences, logged_in_api_client, factories):
    app = factories["users.Application"](user=logged_in_api_client.user)
    url = reverse("api:v1:oauth:apps-detail", kwargs={"client_id": app.client_id})
    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert response.data == serializers.CreateApplicationSerializer(app).data
    assert response.data["token"] == app.token


def test_apps_refresh_token(preferences, logged_in_api_client, factories):
    app = factories["users.Application"](user=logged_in_api_client.user)
    old_token = app.token
    url = reverse(
        "api:v1:oauth:apps-refresh_token", kwargs={"client_id": app.client_id}
    )
    response = logged_in_api_client.post(url)

    app.refresh_from_db()
    assert response.status_code == 200
    assert response.data == serializers.CreateApplicationSerializer(app).data
    assert app.token != old_token


def test_apps_refresh_token_not_owner(preferences, logged_in_api_client, factories):
    app = factories["users.Application"]()
    url = reverse(
        "api:v1:oauth:apps-refresh_token", kwargs={"client_id": app.client_id}
    )
    response = logged_in_api_client.post(url)

    assert response.status_code == 404


def test_authorize_view_post(logged_in_client, factories):
    app = factories["users.Application"]()
    url = reverse("api:v1:oauth:authorize")
    response = logged_in_client.post(
        url,
        {
            "allow": True,
            "redirect_uri": app.redirect_uris,
            "client_id": app.client_id,
            "state": "hello",
            "response_type": "code",
            "scope": "read",
        },
    )
    grant = models.Grant.objects.get(application=app)
    assert response.status_code == 302
    assert response["Location"] == "{}?code={}&state={}".format(
        app.redirect_uris, grant.code, "hello"
    )


def test_authorize_view_post_ajax_no_redirect(logged_in_client, factories):
    app = factories["users.Application"]()
    url = reverse("api:v1:oauth:authorize")
    response = logged_in_client.post(
        url,
        {
            "allow": True,
            "redirect_uri": app.redirect_uris,
            "client_id": app.client_id,
            "state": "hello",
            "response_type": "code",
            "scope": "read",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert response.status_code == 200
    grant = models.Grant.objects.get(application=app)
    assert json.loads(response.content.decode()) == {
        "redirect_uri": "{}?code={}&state={}".format(
            app.redirect_uris, grant.code, "hello"
        ),
        "code": grant.code,
    }


def test_authorize_view_post_ajax_oob(logged_in_client, factories):
    app = factories["users.Application"](redirect_uris="urn:ietf:wg:oauth:2.0:oob")
    url = reverse("api:v1:oauth:authorize")
    response = logged_in_client.post(
        url,
        {
            "allow": True,
            "redirect_uri": app.redirect_uris,
            "client_id": app.client_id,
            "state": "hello",
            "response_type": "code",
            "scope": "read",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert response.status_code == 200
    grant = models.Grant.objects.get(application=app)
    assert json.loads(response.content.decode()) == {
        "redirect_uri": "{}?code={}&state={}".format(
            app.redirect_uris, grant.code, "hello"
        ),
        "code": grant.code,
    }


def test_authorize_view_invalid_form(logged_in_client, factories):
    url = reverse("api:v1:oauth:authorize")
    response = logged_in_client.post(
        url,
        {
            "allow": True,
            "redirect_uri": "",
            "client_id": "Noop",
            "state": "hello",
            "response_type": "code",
            "scope": "read",
        },
    )

    assert response.status_code == 400
    assert json.loads(response.content.decode()) == {
        "redirect_uri": ["This field is required."]
    }


def test_authorize_view_invalid_redirect_url(logged_in_client, factories):
    app = factories["users.Application"]()
    url = reverse("api:v1:oauth:authorize")
    response = logged_in_client.post(
        url,
        {
            "allow": True,
            "redirect_uri": "http://wrong.url",
            "client_id": app.client_id,
            "state": "hello",
            "response_type": "code",
            "scope": "read",
        },
    )

    assert response.status_code == 400
    assert json.loads(response.content.decode()) == {
        "detail": "Mismatching redirect URI."
    }


def test_authorize_view_invalid_oauth(logged_in_client, factories):
    app = factories["users.Application"]()
    url = reverse("api:v1:oauth:authorize")
    response = logged_in_client.post(
        url,
        {
            "allow": True,
            "redirect_uri": app.redirect_uris,
            "client_id": "wrong_id",
            "state": "hello",
            "response_type": "code",
            "scope": "read",
        },
    )

    assert response.status_code == 400
    assert json.loads(response.content.decode()) == {
        "non_field_errors": ["Invalid application"]
    }


def test_authorize_view_anonymous(client, factories):
    url = reverse("api:v1:oauth:authorize")
    response = client.post(url, {})

    assert response.status_code == 401


def test_token_view_post(api_client, factories):
    grant = factories["users.Grant"]()
    app = grant.application
    url = reverse("api:v1:oauth:token")

    response = api_client.post(
        url,
        {
            "redirect_uri": app.redirect_uris,
            "client_id": app.client_id,
            "client_secret": app.client_secret,
            "grant_type": "authorization_code",
            "code": grant.code,
        },
    )
    payload = json.loads(response.content.decode())

    assert "access_token" in payload
    assert "refresh_token" in payload
    assert payload["expires_in"] == 36000
    assert payload["scope"] == grant.scope
    assert payload["token_type"] == "Bearer"
    assert response.status_code == 200

    with pytest.raises(grant.DoesNotExist):
        grant.refresh_from_db()

    token = payload["access_token"]

    # Now check we can use the token for auth
    response = api_client.get(
        reverse("api:v1:users:users-me"), HTTP_AUTHORIZATION="Bearer {}".format(token)
    )
    assert response.status_code == 200


def test_revoke_view_post(logged_in_client, factories):
    token = factories["users.AccessToken"]()
    url = reverse("api:v1:oauth:revoke")

    response = logged_in_client.post(
        url,
        {
            "token": token.token,
            "client_id": token.application.client_id,
            "client_secret": token.application.client_secret,
        },
    )
    assert response.status_code == 200

    with pytest.raises(token.DoesNotExist):
        token.refresh_from_db()


def test_grants_list(factories, logged_in_api_client):
    token = factories["users.AccessToken"](user=logged_in_api_client.user)
    refresh_token = factories["users.RefreshToken"](user=logged_in_api_client.user)
    factories["users.AccessToken"]()
    url = reverse("api:v1:oauth:grants-list")
    expected = [
        serializers.ApplicationSerializer(refresh_token.application).data,
        serializers.ApplicationSerializer(token.application).data,
    ]

    response = logged_in_api_client.get(url)

    assert response.status_code == 200
    assert response.data == expected


def test_grant_delete(factories, logged_in_api_client, mocker, now):
    token = factories["users.AccessToken"](user=logged_in_api_client.user)
    refresh_token = factories["users.RefreshToken"](
        user=logged_in_api_client.user, application=token.application
    )
    grant = factories["users.Grant"](
        user=logged_in_api_client.user, application=token.application
    )
    revoke_token = mocker.spy(token.__class__, "revoke")
    revoke_refresh = mocker.spy(refresh_token.__class__, "revoke")
    to_keep = [
        factories["users.AccessToken"](application=token.application),
        factories["users.RefreshToken"](application=token.application),
        factories["users.Grant"](application=token.application),
    ]
    url = reverse(
        "api:v1:oauth:grants-detail", kwargs={"client_id": token.application.client_id}
    )

    response = logged_in_api_client.delete(url)

    assert response.status_code == 204

    revoke_token.assert_called_once()
    revoke_refresh.assert_called_once()

    with pytest.raises(token.DoesNotExist):
        token.refresh_from_db()

    with pytest.raises(grant.DoesNotExist):
        grant.refresh_from_db()

    refresh_token.refresh_from_db()
    assert refresh_token.revoked == now

    for t in to_keep:
        t.refresh_from_db()


@pytest.mark.parametrize(
    "setting_value, verified_email, expected_status_code",
    [
        ("mandatory", False, 401),
        ("mandatory", True, 200),
        ("optional", True, 200),
        ("optional", False, 200),
    ],
)
def test_token_auth(
    setting_value,
    verified_email,
    expected_status_code,
    api_client,
    factories,
    settings,
    mailoutbox,
):
    sent_emails = len(mailoutbox)
    user = factories["users.User"](verified_email=verified_email)
    token = factories["users.AccessToken"](user=user)
    settings.ACCOUNT_EMAIL_VERIFICATION = setting_value
    response = api_client.get(
        reverse("api:v1:users:users-me"),
        HTTP_AUTHORIZATION="Bearer {}".format(token.token),
    )
    assert response.status_code == expected_status_code

    if expected_status_code != 200:
        # confirmation email should have been sent again
        assert len(mailoutbox) == sent_emails + 1

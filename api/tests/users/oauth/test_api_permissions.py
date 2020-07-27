import pytest
import uuid

from django.urls import reverse

from funkwhale_api.users.oauth import scopes

# mutations


@pytest.mark.parametrize(
    "name, url_kwargs, scope, method",
    [
        ("api:v1:search", {}, "read:libraries", "get"),
        ("api:v1:artists-list", {}, "read:libraries", "get"),
        ("api:v1:albums-list", {}, "read:libraries", "get"),
        ("api:v1:tracks-list", {}, "read:libraries", "get"),
        ("api:v1:tracks-mutations", {"pk": 42}, "read:edits", "get"),
        ("api:v1:tags-list", {}, "read:libraries", "get"),
        ("api:v1:licenses-list", {}, "read:libraries", "get"),
        ("api:v1:moderation:content-filters-list", {}, "read:filters", "get"),
        ("api:v1:listen-detail", {"uuid": uuid.uuid4()}, "read:libraries", "get"),
        ("api:v1:uploads-list", {}, "read:libraries", "get"),
        ("api:v1:playlists-list", {}, "read:playlists", "get"),
        ("api:v1:favorites:tracks-list", {}, "read:favorites", "get"),
        ("api:v1:history:listenings-list", {}, "read:listenings", "get"),
        ("api:v1:radios:radios-list", {}, "read:radios", "get"),
        ("api:v1:oauth:grants-list", {}, "read:security", "get"),
        ("api:v1:federation:inbox-list", {}, "read:notifications", "get"),
        (
            "api:v1:federation:libraries-detail",
            {"uuid": uuid.uuid4()},
            "read:libraries",
            "get",
        ),
        ("api:v1:federation:library-follows-list", {}, "read:follows", "get"),
        ("api:v1:tags-list", {}, "read:libraries", "get"),
        # admin / privileged stuff
        ("api:v1:instance:admin-settings-list", {}, "read:instance:settings", "get"),
        (
            "api:v1:manage:users:invitations-list",
            {},
            "read:instance:invitations",
            "get",
        ),
        ("api:v1:manage:users:users-list", {}, "read:instance:users", "get"),
        ("api:v1:manage:library:uploads-list", {}, "read:instance:libraries", "get"),
        ("api:v1:manage:accounts-list", {}, "read:instance:accounts", "get"),
        ("api:v1:manage:federation:domains-list", {}, "read:instance:domains", "get"),
        (
            "api:v1:manage:moderation:instance-policies-list",
            {},
            "read:instance:policies",
            "get",
        ),
        ("api:v1:manage:library:artists-list", {}, "read:instance:libraries", "get"),
    ],
)
def test_views_permissions(
    name, url_kwargs, scope, method, mocker, logged_in_api_client
):
    """
    Smoke tests to ensure viewsets are correctly protected
    """
    url = reverse(name, kwargs=url_kwargs)
    user_scopes = scopes.get_from_permissions(
        **logged_in_api_client.user.get_permissions()
    )

    should_allow = mocker.patch(
        "funkwhale_api.users.oauth.permissions.should_allow", return_value=False
    )
    handler = getattr(logged_in_api_client, method)
    response = handler(url)
    should_allow.assert_called_once_with(
        required_scope=scope, request_scopes=user_scopes
    )
    assert response.status_code == 403, "{} on {} is not protected correctly!".format(
        method, url
    )

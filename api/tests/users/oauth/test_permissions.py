import pytest

from funkwhale_api.users.oauth import scopes
from funkwhale_api.users.oauth import permissions


@pytest.mark.parametrize(
    "required_scope, request_scopes, expected",
    [
        (None, {}, True),
        ("write:profile", {"write"}, True),
        ("write:profile", {"read"}, False),
        ("write:profile", {"read:profile"}, False),
        ("write:profile", {"write:profile"}, True),
        ("read:profile", {"read"}, True),
        ("read:profile", {"write"}, False),
        ("read:profile", {"read:profile"}, True),
        ("read:profile", {"write:profile"}, False),
        ("write:profile", {"write"}, True),
        ("write:profile", {"read:profile"}, False),
        ("write:profile", {"write:profile"}, True),
        ("write:profile", {"write"}, True),
        ("write:profile", {"read:profile"}, False),
        ("write:profile", {"write:profile"}, True),
        ("write:profile", {"write"}, True),
        ("write:profile", {"read:profile"}, False),
        ("write:profile", {"write:profile"}, True),
    ],
)
def test_should_allow(required_scope, request_scopes, expected):
    assert (
        permissions.should_allow(
            required_scope=required_scope, request_scopes=request_scopes
        )
        is expected
    )


@pytest.mark.parametrize("method", ["OPTIONS", "HEAD"])
def test_scope_permission_safe_methods(method, mocker, factories):
    view = mocker.Mock(required_scope="write:profile", anonymous_policy=False)
    request = mocker.Mock(method=method)

    p = permissions.ScopePermission()

    assert p.has_permission(request, view) is True


@pytest.mark.parametrize(
    "policy, preference, expected",
    [
        (True, False, True),
        (False, False, False),
        ("setting", True, False),
        ("setting", False, True),
    ],
)
def test_scope_permission_anonymous_policy(
    policy, preference, expected, preferences, mocker, anonymous_user
):
    preferences["common__api_authentication_required"] = preference
    view = mocker.Mock(
        required_scope="libraries", anonymous_policy=policy, anonymous_scopes=set()
    )
    request = mocker.Mock(method="GET", user=anonymous_user, actor=None, scopes=None)

    p = permissions.ScopePermission()

    assert p.has_permission(request, view) is expected


def test_scope_permission_dict_no_required(mocker, anonymous_user):
    view = mocker.Mock(
        required_scope={"read": None, "write": "write:profile"},
        anonymous_policy=True,
        action="read",
        anonymous_scopes=set(),
    )
    request = mocker.Mock(method="GET", user=anonymous_user, actor=None, scopes=None)

    p = permissions.ScopePermission()

    assert p.has_permission(request, view) is True


@pytest.mark.parametrize(
    "required_scope, method, action, expected_scope",
    [
        ("profile", "GET", "read", "read:profile"),
        ("profile", "POST", "write", "write:profile"),
        ({"read": "read:profile"}, "GET", "read", "read:profile"),
        ({"write": "write:profile"}, "POST", "write", "write:profile"),
    ],
)
def test_scope_permission_user(
    required_scope, method, action, expected_scope, mocker, factories
):
    user = factories["users.User"]()
    should_allow = mocker.patch.object(permissions, "should_allow")
    request = mocker.Mock(method=method, user=user, actor=None, scopes=None)
    view = mocker.Mock(
        required_scope=required_scope, anonymous_policy=False, action=action
    )

    p = permissions.ScopePermission()

    assert p.has_permission(request, view) == should_allow.return_value

    should_allow.assert_called_once_with(
        required_scope=expected_scope,
        request_scopes=scopes.get_from_permissions(**user.get_permissions()),
    )


def test_scope_permission_token(mocker, factories):
    token = factories["users.AccessToken"](
        scope="write:profile read:playlists",
        application__scope="write:profile read:playlists",
    )
    should_allow = mocker.patch.object(permissions, "should_allow")
    request = mocker.Mock(method="POST", auth=token)
    view = mocker.Mock(required_scope="profile", anonymous_policy=False)

    p = permissions.ScopePermission()

    assert p.has_permission(request, view) == should_allow.return_value

    should_allow.assert_called_once_with(
        required_scope="write:profile",
        request_scopes={"write:profile", "read:playlists"},
    )


def test_scope_permission_request_scopes(mocker, factories):
    should_allow = mocker.patch.object(permissions, "should_allow")
    request = mocker.Mock(method="POST", scopes=["write:profile", "read:playlists"])
    view = mocker.Mock(required_scope="profile", anonymous_policy=False)
    p = permissions.ScopePermission()

    assert p.has_permission(request, view) == should_allow.return_value

    should_allow.assert_called_once_with(
        required_scope="write:profile",
        request_scopes={"write:profile", "read:playlists"},
    )


def test_scope_permission_actor(mocker, factories, anonymous_user):
    should_allow = mocker.patch.object(permissions, "should_allow")
    request = mocker.Mock(
        method="POST",
        actor=factories["federation.Actor"](),
        user=anonymous_user,
        scopes=None,
    )
    view = mocker.Mock(required_scope="profile", anonymous_policy=False)
    p = permissions.ScopePermission()

    assert p.has_permission(request, view) == should_allow.return_value

    should_allow.assert_called_once_with(
        required_scope="write:profile", request_scopes=scopes.FEDERATION_REQUEST_SCOPES
    )


def test_scope_permission_token_anonymous_user_auth_required(
    mocker, factories, anonymous_user, preferences
):
    preferences["common__api_authentication_required"] = True
    should_allow = mocker.patch.object(permissions, "should_allow")
    request = mocker.Mock(method="POST", user=anonymous_user, actor=None, scopes=None)
    view = mocker.Mock(required_scope="profile", anonymous_policy=False)

    p = permissions.ScopePermission()

    assert p.has_permission(request, view) is False

    should_allow.assert_not_called()


def test_scope_permission_token_anonymous_user_auth_not_required(
    mocker, factories, anonymous_user, preferences
):
    preferences["common__api_authentication_required"] = False
    should_allow = mocker.patch.object(permissions, "should_allow")
    request = mocker.Mock(method="POST", user=anonymous_user, actor=None, scopes=None)
    view = mocker.Mock(
        required_scope="profile", anonymous_policy="setting", anonymous_scopes=set()
    )

    p = permissions.ScopePermission()

    assert p.has_permission(request, view) == should_allow.return_value

    should_allow.assert_called_once_with(
        required_scope="write:profile", request_scopes=scopes.ANONYMOUS_SCOPES
    )


def test_scope_permission_token_expired(mocker, factories, now):
    token = factories["users.AccessToken"](
        scope="profile:write playlists:read", expires=now
    )
    should_allow = mocker.patch.object(permissions, "should_allow")
    request = mocker.Mock(method="POST", auth=token)
    view = mocker.Mock(required_scope="profile", anonymous_policy=False)

    p = permissions.ScopePermission()

    assert p.has_permission(request, view) is False

    should_allow.assert_not_called()


def test_scope_permission_token_no_user(mocker, factories, now):
    token = factories["users.AccessToken"](
        scope="profile:write playlists:read", user=None
    )
    should_allow = mocker.patch.object(permissions, "should_allow")
    request = mocker.Mock(method="POST", auth=token)
    view = mocker.Mock(required_scope="profile", anonymous_policy=False)

    p = permissions.ScopePermission()

    assert p.has_permission(request, view) is False

    should_allow.assert_not_called()


def test_scope_permission_token_honor_app_scopes(mocker, factories, now):
    # token contains read access, but app scope only allows profile:write
    token = factories["users.AccessToken"](
        scope="write:profile read", application__scope="write:profile"
    )
    should_allow = mocker.patch.object(permissions, "should_allow")
    request = mocker.Mock(method="POST", auth=token)
    view = mocker.Mock(required_scope="profile", anonymous_policy=False)

    p = permissions.ScopePermission()

    assert p.has_permission(request, view) == should_allow.return_value

    should_allow.assert_called_once_with(
        required_scope="write:profile", request_scopes={"write:profile"}
    )


def test_scope_permission_token_honor_allowed_app_scopes(mocker, factories, now):
    mocker.patch.object(scopes, "OAUTH_APP_SCOPES", {"read:profile"})
    token = factories["users.AccessToken"](
        scope="write:profile read:profile read",
        application__scope="write:profile read:profile read",
    )
    should_allow = mocker.patch.object(permissions, "should_allow")
    request = mocker.Mock(method="POST", auth=token)
    view = mocker.Mock(required_scope="profile", anonymous_policy=False)
    p = permissions.ScopePermission()

    assert p.has_permission(request, view) == should_allow.return_value

    should_allow.assert_called_once_with(
        required_scope="write:profile", request_scopes={"read:profile"}
    )

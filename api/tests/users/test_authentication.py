import pytest

from django.core import signing

from funkwhale_api.users import authentication


def test_generate_scoped_token(mocker):
    dumps = mocker.patch("django.core.signing.dumps")

    result = authentication.generate_scoped_token(
        user_id=42, user_secret="hello", scopes=["read"],
    )

    assert result == dumps.return_value
    dumps.assert_called_once_with(
        {"scopes": ["read"], "user_secret": "hello", "user_id": 42},
        salt="scoped_tokens",
    )


def test_authenticate_scoped_token(mocker, factories, settings):
    loads = mocker.spy(signing, "loads")
    user = factories["users.User"]()
    token = signing.dumps(
        {"user_id": user.pk, "user_secret": str(user.secret_key), "scopes": ["read"]},
        salt="scoped_tokens",
    )

    logged_user, scopes = authentication.authenticate_scoped_token(token)

    assert scopes == ["read"]
    assert logged_user == user
    loads.assert_called_once_with(
        token, salt="scoped_tokens", max_age=settings.SCOPED_TOKENS_MAX_AGE
    )


def test_authenticate_scoped_token_bad_signature():
    with pytest.raises(authentication.exceptions.AuthenticationFailed):
        authentication.authenticate_scoped_token("hello")


def test_authenticate_scoped_token_bad_secret_key(factories):
    user = factories["users.User"]()
    token = authentication.generate_scoped_token(
        user_id=user.pk, user_secret="invalid", scopes=["read"]
    )

    with pytest.raises(authentication.exceptions.AuthenticationFailed):
        authentication.authenticate_scoped_token(token)


def test_scope_token_authentication(fake_request, factories, mocker):
    user = factories["users.User"]()
    actor = user.create_actor()
    authenticate_scoped_token = mocker.spy(authentication, "authenticate_scoped_token")
    token = authentication.generate_scoped_token(
        user_id=user.pk, user_secret=user.secret_key, scopes=["read"]
    )
    request = fake_request.get("/", {"token": token})
    auth = authentication.ScopedTokenAuthentication()

    assert auth.authenticate(request) == (user, None)
    assert request.scopes == ["read"]
    assert request.actor == actor
    authenticate_scoped_token.assert_called_once_with(token)


def test_scope_token_invalid(fake_request, factories):
    token = "test"
    request = fake_request.get("/", {"token": token})
    auth = authentication.ScopedTokenAuthentication()

    with pytest.raises(authentication.exceptions.AuthenticationFailed):
        auth.authenticate(request)


def test_scope_token_missing(fake_request, factories):
    request = fake_request.get("/")
    auth = authentication.ScopedTokenAuthentication()

    assert auth.authenticate(request) is None

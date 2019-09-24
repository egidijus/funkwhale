import pytest

from funkwhale_api import plugins

from funkwhale_api.common import authentication as common_authentication
from funkwhale_api.subsonic import authentication as subsonic_authentication


@pytest.mark.parametrize(
    "authentication_class, base_class, patched_method",
    [
        (
            common_authentication.SessionAuthentication,
            common_authentication.BaseSessionAuthentication,
            "authenticate",
        ),
        (
            common_authentication.JSONWebTokenAuthentication,
            common_authentication.authentication.JSONWebTokenAuthentication,
            "authenticate",
        ),
        (
            common_authentication.JSONWebTokenAuthenticationQS,
            common_authentication.authentication.BaseJSONWebTokenAuthentication,
            "authenticate",
        ),
        (
            common_authentication.OAuth2Authentication,
            common_authentication.BaseOAuth2Authentication,
            "authenticate",
        ),
        (
            common_authentication.BearerTokenHeaderAuth,
            common_authentication.authentication.BaseJSONWebTokenAuthentication,
            "authenticate",
        ),
        (
            subsonic_authentication.SubsonicAuthentication,
            subsonic_authentication.SubsonicAuthentication,
            "perform_authentication",
        ),
    ],
)
def test_authentication_calls_update_plugins_conf_with_user_settings(
    authentication_class, base_class, patched_method, mocker, api_request
):
    request = api_request.get("/")
    plugins_conf = mocker.Mock()
    setattr(request, "plugins_conf", plugins_conf)
    auth = (mocker.Mock(), None)
    authentication = authentication_class()
    base_class_authenticate = mocker.patch.object(
        base_class, patched_method, return_value=auth
    )
    update_plugins_conf_with_user_settings = mocker.patch.object(
        plugins, "update_plugins_conf_with_user_settings"
    )

    authentication.authenticate(request)

    update_plugins_conf_with_user_settings.assert_called_once_with(
        plugins_conf, user=auth[0]
    )
    base_class_authenticate.assert_called_once_with(request)

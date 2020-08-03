import pytest
from django import urls


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/artists",
        "/api/v1/albums",
        "/api/v1/tracks",
        "/api/v1/libraries",
        "/api/v1/uploads",
        "/api/v1/playlists",
        "/api/v1/favorites/tracks",
        "/api/v1/auth/registration/verify-email",
        "/api/v1/auth/registration/change-password",
        "/api/v1/auth/registration/account-confirm-email/key",
        "/api/v1/history/listenings",
        "/api/v1/radios/sessions",
        "/api/v1/users/me",
        "/api/v1/federation/follows/library",
        "/api/v1/manage/accounts",
        "/api/v1/oauth/apps",
        "/api/v1/moderation/content-filters",
        "/api/v1/token",
        "/api/v1/token/refresh",
        "/api/v1/instance/settings",
        "/api/v1/instance/nodeinfo/2.0",
    ],
)
@pytest.mark.parametrize("suffix", ["", "/"])
def test_optional_trailing_slash(url, suffix):
    match = urls.resolve(url + suffix)
    assert match is not None

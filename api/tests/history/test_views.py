import pytest

from django.urls import reverse

from funkwhale_api import plugins


@pytest.mark.parametrize("level", ["instance", "me", "followers"])
def test_privacy_filter(preferences, level, factories, api_client):
    preferences["common__api_authentication_required"] = False
    factories["history.Listening"](user__privacy_level=level)
    url = reverse("api:v1:history:listenings-list")
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.data["count"] == 0


def test_now(factories, logged_in_api_client, plugins_conf, mocker):
    track = factories["music.Track"]()
    url = reverse("api:v1:history:listenings-now")
    on_commit = mocker.patch("funkwhale_api.common.utils.on_commit")
    response = logged_in_api_client.post(url, {"track": track.pk})

    on_commit.assert_called_once_with(
        plugins.hooks.dispatch,
        "history.listening.now",
        track=track,
        user=logged_in_api_client.user,
        plugins_conf=plugins_conf,
    )

    assert response.status_code == 204

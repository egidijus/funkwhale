from funkwhale_api import plugins
from funkwhale_api.federation import serializers as federation_serializers
from funkwhale_api.history import serializers
from funkwhale_api.music import serializers as music_serializers
from funkwhale_api.users import serializers as users_serializers


def test_listening_serializer(factories, to_api_date):
    listening = factories["history.Listening"]()
    actor = listening.user.create_actor()

    expected = {
        "id": listening.pk,
        "creation_date": to_api_date(listening.creation_date),
        "track": music_serializers.TrackSerializer(listening.track).data,
        "actor": federation_serializers.APIActorSerializer(actor).data,
        "user": users_serializers.UserBasicSerializer(listening.user).data,
    }
    serializer = serializers.ListeningSerializer(listening)

    assert serializer.data == expected


def test_listening_create(factories, to_api_date, mocker, now):
    user = factories["users.User"]()
    track = factories["music.Track"]()
    payload = {"track": track.pk}
    on_commit = mocker.patch("funkwhale_api.common.utils.on_commit")
    request = mocker.Mock(plugins_conf=mocker.Mock())
    serializer = serializers.ListeningWriteSerializer(
        data=payload, context={"request": request, "user": user}
    )

    assert serializer.is_valid(raise_exception=True) is True
    listening = serializer.save()

    assert serializer.instance.user == user
    assert serializer.instance.track == track

    on_commit.assert_called_once_with(
        plugins.hooks.dispatch,
        "history.listening.created",
        listening=listening,
        plugins_conf=request.plugins_conf,
    )

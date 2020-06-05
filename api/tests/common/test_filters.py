import pytest

from funkwhale_api.common import filters


@pytest.mark.parametrize(
    "value, expected",
    [
        (True, True),
        ("True", True),
        ("true", True),
        ("1", True),
        ("yes", True),
        (False, False),
        ("False", False),
        ("false", False),
        ("0", False),
        ("no", False),
        ("None", None),
        ("none", None),
        ("Null", None),
        ("null", None),
    ],
)
def test_mutation_filter_is_approved(value, expected, factories):
    mutations = {
        True: factories["common.Mutation"](is_approved=True, payload={}),
        False: factories["common.Mutation"](is_approved=False, payload={}),
        None: factories["common.Mutation"](is_approved=None, payload={}),
    }

    qs = mutations[True].__class__.objects.all()

    filterset = filters.MutationFilter(
        {"q": "is_approved:{}".format(value)}, queryset=qs
    )

    assert list(filterset.qs) == [mutations[expected]]


@pytest.mark.parametrize(
    "scope, user_index, expected_tracks",
    [
        ("me", 0, [0]),
        ("me", 1, [1]),
        ("me", 2, []),
        ("all", 0, [0, 1, 2]),
        ("all", 1, [0, 1, 2]),
        ("all", 2, [0, 1, 2]),
        ("noop", 0, []),
        ("noop", 1, []),
        ("noop", 2, []),
        ("actor:actor1@domain.test", 0, [0]),
        ("actor:actor2@domain.test", 0, [1]),
        ("domain:domain.test", 0, [0, 1]),
    ],
)
def test_actor_scope_filter(
    scope,
    user_index,
    expected_tracks,
    queryset_equal_list,
    factories,
    mocker,
    anonymous_user,
):
    domain = factories["federation.Domain"](name="domain.test")
    actor1 = factories["users.User"]().create_actor(
        preferred_username="actor1", domain=domain
    )
    actor2 = factories["users.User"]().create_actor(
        preferred_username="actor2", domain=domain
    )
    users = [actor1.user, actor2.user, anonymous_user]
    tracks = [
        factories["music.Upload"](library__actor=actor1, playable=True).track,
        factories["music.Upload"](library__actor=actor2, playable=True).track,
        factories["music.Upload"](playable=True).track,
    ]

    class FS(filters.filters.FilterSet):
        scope = filters.ActorScopeFilter(
            actor_field="uploads__library__actor", distinct=True
        )

        class Meta:
            model = tracks[0].__class__
            fields = ["scope"]

    queryset = tracks[0].__class__.objects.all()
    request = mocker.Mock(user=users[user_index])
    filterset = FS({"scope": scope}, queryset=queryset.order_by("id"), request=request)

    expected = [tracks[i] for i in expected_tracks]

    assert filterset.qs == expected

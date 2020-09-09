import pytest

from django.urls import reverse

import funkwhale_api
from funkwhale_api.instance import nodeinfo
from funkwhale_api.federation import actors
from funkwhale_api.federation import utils as federation_utils
from funkwhale_api.music import utils as music_utils


def test_nodeinfo_dump(preferences, mocker, avatar):
    preferences["instance__banner"] = avatar
    preferences["instance__nodeinfo_stats_enabled"] = True
    preferences["common__api_authentication_required"] = False
    preferences["moderation__unauthenticated_report_types"] = [
        "takedown_request",
        "other",
        "other_category_that_doesnt_exist",
    ]

    stats = {
        "users": {"total": 1, "active_halfyear": 12, "active_month": 13},
        "tracks": 2,
        "albums": 3,
        "artists": 4,
        "track_favorites": 5,
        "music_duration": 6,
        "listenings": 7,
        "downloads": 42,
    }
    mocker.patch("funkwhale_api.instance.stats.get", return_value=stats)

    expected = {
        "version": "2.0",
        "software": {"name": "funkwhale", "version": funkwhale_api.__version__},
        "protocols": ["activitypub"],
        "services": {"inbound": [], "outbound": []},
        "openRegistrations": preferences["users__registration_enabled"],
        "usage": {"users": {"total": 1, "activeHalfyear": 12, "activeMonth": 13}},
        "metadata": {
            "actorId": actors.get_service_actor().fid,
            "private": preferences["instance__nodeinfo_private"],
            "shortDescription": preferences["instance__short_description"],
            "longDescription": preferences["instance__long_description"],
            "nodeName": preferences["instance__name"],
            "rules": preferences["instance__rules"],
            "contactEmail": preferences["instance__contact_email"],
            "defaultUploadQuota": preferences["users__upload_quota"],
            "terms": preferences["instance__terms"],
            "banner": federation_utils.full_url(preferences["instance__banner"].url),
            "library": {
                "federationEnabled": preferences["federation__enabled"],
                "anonymousCanListen": not preferences[
                    "common__api_authentication_required"
                ],
                "tracks": {"total": stats["tracks"]},
                "artists": {"total": stats["artists"]},
                "albums": {"total": stats["albums"]},
                "music": {"hours": stats["music_duration"]},
            },
            "usage": {
                "favorites": {"tracks": {"total": stats["track_favorites"]}},
                "listenings": {"total": stats["listenings"]},
                "downloads": {"total": stats["downloads"]},
            },
            "supportedUploadExtensions": music_utils.SUPPORTED_EXTENSIONS,
            "allowList": {"enabled": False, "domains": None},
            "reportTypes": [
                {
                    "type": "takedown_request",
                    "label": "Takedown request",
                    "anonymous": True,
                },
                {
                    "type": "invalid_metadata",
                    "label": "Invalid metadata",
                    "anonymous": False,
                },
                {
                    "type": "illegal_content",
                    "label": "Illegal content",
                    "anonymous": False,
                },
                {
                    "type": "offensive_content",
                    "label": "Offensive content",
                    "anonymous": False,
                },
                {"type": "other", "label": "Other", "anonymous": True},
            ],
            "funkwhaleSupportMessageEnabled": preferences[
                "instance__funkwhale_support_message_enabled"
            ],
            "instanceSupportMessage": preferences["instance__support_message"],
            "endpoints": {
                "knownNodes": federation_utils.full_url(
                    reverse("api:v1:federation:domains-list")
                ),
                "libraries": federation_utils.full_url(
                    reverse("federation:index:index-libraries")
                ),
                "channels": federation_utils.full_url(
                    reverse("federation:index:index-channels")
                ),
            },
        },
    }
    assert nodeinfo.get() == expected


def test_nodeinfo_dump_stats_disabled(preferences, mocker):
    preferences["instance__nodeinfo_stats_enabled"] = False
    preferences["federation__public_index"] = False
    preferences["moderation__unauthenticated_report_types"] = [
        "takedown_request",
        "other",
    ]

    expected = {
        "version": "2.0",
        "software": {"name": "funkwhale", "version": funkwhale_api.__version__},
        "protocols": ["activitypub"],
        "services": {"inbound": [], "outbound": []},
        "openRegistrations": preferences["users__registration_enabled"],
        "usage": {"users": {"total": 0, "activeHalfyear": 0, "activeMonth": 0}},
        "metadata": {
            "actorId": actors.get_service_actor().fid,
            "private": preferences["instance__nodeinfo_private"],
            "shortDescription": preferences["instance__short_description"],
            "longDescription": preferences["instance__long_description"],
            "nodeName": preferences["instance__name"],
            "rules": preferences["instance__rules"],
            "contactEmail": preferences["instance__contact_email"],
            "defaultUploadQuota": preferences["users__upload_quota"],
            "terms": preferences["instance__terms"],
            "banner": None,
            "library": {
                "federationEnabled": preferences["federation__enabled"],
                "anonymousCanListen": not preferences[
                    "common__api_authentication_required"
                ],
            },
            "supportedUploadExtensions": music_utils.SUPPORTED_EXTENSIONS,
            "allowList": {"enabled": False, "domains": None},
            "reportTypes": [
                {
                    "type": "takedown_request",
                    "label": "Takedown request",
                    "anonymous": True,
                },
                {
                    "type": "invalid_metadata",
                    "label": "Invalid metadata",
                    "anonymous": False,
                },
                {
                    "type": "illegal_content",
                    "label": "Illegal content",
                    "anonymous": False,
                },
                {
                    "type": "offensive_content",
                    "label": "Offensive content",
                    "anonymous": False,
                },
                {"type": "other", "label": "Other", "anonymous": True},
            ],
            "funkwhaleSupportMessageEnabled": preferences[
                "instance__funkwhale_support_message_enabled"
            ],
            "instanceSupportMessage": preferences["instance__support_message"],
            "endpoints": {"knownNodes": None, "libraries": None, "channels": None},
        },
    }
    assert nodeinfo.get() == expected


@pytest.mark.parametrize(
    "enabled, public, expected",
    [
        (True, True, {"enabled": True, "domains": ["allowed.example"]}),
        (True, False, {"enabled": True, "domains": None}),
        (False, False, {"enabled": False, "domains": None}),
    ],
)
def test_nodeinfo_allow_list_enabled(preferences, factories, enabled, public, expected):
    preferences["moderation__allow_list_enabled"] = enabled
    preferences["moderation__allow_list_public"] = public
    factories["federation.Domain"](name="allowed.example", allowed=True)
    factories["federation.Domain"](allowed=False)
    factories["federation.Domain"](allowed=None)

    assert nodeinfo.get()["metadata"]["allowList"] == expected

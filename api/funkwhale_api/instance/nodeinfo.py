import memoize.djangocache

from django.urls import reverse

import funkwhale_api
from funkwhale_api.common import preferences
from funkwhale_api.federation import actors, models as federation_models
from funkwhale_api.federation import utils as federation_utils
from funkwhale_api.moderation import models as moderation_models
from funkwhale_api.music import utils as music_utils

from . import stats

store = memoize.djangocache.Cache("default")
memo = memoize.Memoizer(store, namespace="instance:stats")


def get():
    all_preferences = preferences.all()
    share_stats = all_preferences.get("instance__nodeinfo_stats_enabled")
    allow_list_enabled = all_preferences.get("moderation__allow_list_enabled")
    allow_list_public = all_preferences.get("moderation__allow_list_public")
    auth_required = all_preferences.get("common__api_authentication_required")
    banner = all_preferences.get("instance__banner")
    unauthenticated_report_types = all_preferences.get(
        "moderation__unauthenticated_report_types"
    )
    if allow_list_enabled and allow_list_public:
        allowed_domains = list(
            federation_models.Domain.objects.filter(allowed=True)
            .order_by("name")
            .values_list("name", flat=True)
        )
    else:
        allowed_domains = None
    data = {
        "version": "2.0",
        "software": {"name": "funkwhale", "version": funkwhale_api.__version__},
        "protocols": ["activitypub"],
        "services": {"inbound": [], "outbound": []},
        "openRegistrations": all_preferences.get("users__registration_enabled"),
        "usage": {"users": {"total": 0, "activeHalfyear": 0, "activeMonth": 0}},
        "metadata": {
            "actorId": actors.get_service_actor().fid,
            "private": all_preferences.get("instance__nodeinfo_private"),
            "shortDescription": all_preferences.get("instance__short_description"),
            "longDescription": all_preferences.get("instance__long_description"),
            "rules": all_preferences.get("instance__rules"),
            "contactEmail": all_preferences.get("instance__contact_email"),
            "terms": all_preferences.get("instance__terms"),
            "nodeName": all_preferences.get("instance__name"),
            "banner": federation_utils.full_url(banner.url) if banner else None,
            "defaultUploadQuota": all_preferences.get("users__upload_quota"),
            "library": {
                "federationEnabled": all_preferences.get("federation__enabled"),
                "anonymousCanListen": not all_preferences.get(
                    "common__api_authentication_required"
                ),
            },
            "supportedUploadExtensions": music_utils.SUPPORTED_EXTENSIONS,
            "allowList": {"enabled": allow_list_enabled, "domains": allowed_domains},
            "reportTypes": [
                {"type": t, "label": l, "anonymous": t in unauthenticated_report_types}
                for t, l in moderation_models.REPORT_TYPES
            ],
            "funkwhaleSupportMessageEnabled": all_preferences.get(
                "instance__funkwhale_support_message_enabled"
            ),
            "instanceSupportMessage": all_preferences.get("instance__support_message"),
            "endpoints": {"knownNodes": None, "channels": None, "libraries": None},
        },
    }

    if share_stats:
        getter = memo(lambda: stats.get(), max_age=600)
        statistics = getter()
        data["usage"]["users"]["total"] = statistics["users"]["total"]
        data["usage"]["users"]["activeHalfyear"] = statistics["users"][
            "active_halfyear"
        ]
        data["usage"]["users"]["activeMonth"] = statistics["users"]["active_month"]
        data["metadata"]["library"]["tracks"] = {"total": statistics["tracks"]}
        data["metadata"]["library"]["artists"] = {"total": statistics["artists"]}
        data["metadata"]["library"]["albums"] = {"total": statistics["albums"]}
        data["metadata"]["library"]["music"] = {"hours": statistics["music_duration"]}

        data["metadata"]["usage"] = {
            "favorites": {"tracks": {"total": statistics["track_favorites"]}},
            "listenings": {"total": statistics["listenings"]},
            "downloads": {"total": statistics["downloads"]},
        }
        if not auth_required:
            data["metadata"]["endpoints"]["knownNodes"] = federation_utils.full_url(
                reverse("api:v1:federation:domains-list")
            )
    if not auth_required and preferences.get("federation__public_index"):
        data["metadata"]["endpoints"]["libraries"] = federation_utils.full_url(
            reverse("federation:index:index-libraries")
        )
        data["metadata"]["endpoints"]["channels"] = federation_utils.full_url(
            reverse("federation:index:index-channels")
        )
    return data

from dynamic_preferences import types
from dynamic_preferences.registries import global_preferences_registry

from funkwhale_api.common import preferences

federation = types.Section("federation")


@global_preferences_registry.register
class MusicCacheDuration(types.IntPreference):
    show_in_api = True
    section = federation
    name = "music_cache_duration"
    default = 60 * 24 * 2
    verbose_name = "Music cache duration"
    help_text = (
        "How many minutes do you want to keep a copy of federated tracks "
        "locally? Federated files that were not listened in this interval "
        "will be erased and refetched from the remote on the next listening."
    )
    field_kwargs = {"required": False}


@global_preferences_registry.register
class Enabled(preferences.DefaultFromSettingMixin, types.BooleanPreference):
    section = federation
    name = "enabled"
    setting = "FEDERATION_ENABLED"
    verbose_name = "Federation enabled"
    help_text = (
        "Use this setting to enable or disable federation logic and API" " globally."
    )


@global_preferences_registry.register
class CollectionPageSize(preferences.DefaultFromSettingMixin, types.IntPreference):
    section = federation
    name = "collection_page_size"
    setting = "FEDERATION_COLLECTION_PAGE_SIZE"
    verbose_name = "Federation collection page size"
    help_text = "How many items to display in ActivityPub collections."
    field_kwargs = {"required": False}


@global_preferences_registry.register
class ActorFetchDelay(preferences.DefaultFromSettingMixin, types.IntPreference):
    section = federation
    name = "actor_fetch_delay"
    setting = "FEDERATION_ACTOR_FETCH_DELAY"
    verbose_name = "Federation actor fetch delay"
    help_text = (
        "How many minutes to wait before refetching actors on "
        "request authentication."
    )
    field_kwargs = {"required": False}


@global_preferences_registry.register
class PublicIndex(types.BooleanPreference):
    show_in_api = True
    section = federation
    name = "public_index"
    default = True
    verbose_name = "Enable public index"
    help_text = "If this is enabled, public channels and libraries will be crawlable by other pods and bots"

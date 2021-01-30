from dynamic_preferences import types
from dynamic_preferences.registries import global_preferences_registry

music = types.Section("music")


@global_preferences_registry.register
class MaxTracks(types.BooleanPreference):
    show_in_api = True
    section = music
    name = "transcoding_enabled"
    verbose_name = "Transcoding enabled"
    help_text = (
        "Enable transcoding of audio files in formats requested by the client. "
        "This is especially useful for devices that do not support formats "
        "such as Flac or Ogg, but the transcoding process will increase the "
        "load on the server."
    )
    default = True


@global_preferences_registry.register
class MusicCacheDuration(types.IntPreference):
    show_in_api = True
    section = music
    name = "transcoding_cache_duration"
    default = 60 * 24 * 7
    verbose_name = "Transcoding cache duration"
    help_text = (
        "How many minutes do you want to keep a copy of transcoded tracks "
        "on the server? Transcoded files that were not listened in this interval "
        "will be erased and retranscoded on the next listening."
    )
    field_kwargs = {"required": False}

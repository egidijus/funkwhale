from dynamic_preferences import types
from dynamic_preferences.registries import global_preferences_registry

plugins = types.Section("plugins")


@global_preferences_registry.register
class PluginsEnabled(types.BooleanPreference):
    section = plugins
    show_in_api = True
    name = "enabled"
    default = True
    verbose_name = "Enable Funkwhale plugins"
    help_text = "If disabled, all installed and enabled plugins will be ignored."

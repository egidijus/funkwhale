from dynamic_preferences import types
from dynamic_preferences.registries import global_preferences_registry

common = types.Section("common")


@global_preferences_registry.register
class APIAutenticationRequired(types.BooleanPreference):
    section = common
    name = "api_authentication_required"
    verbose_name = "API Requires authentication"
    default = True
    help_text = (
        "If disabled, anonymous users will be able to query the API "
        "and access music data (as well as other data exposed in the API "
        "without specific permissions)."
    )

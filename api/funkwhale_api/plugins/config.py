from django import forms

from dynamic_preferences import types


SettingSection = types.Section


StringSetting = types.StringPreference


class PasswordSetting(types.StringPreference):
    widget = forms.PasswordInput


class BooleanSetting(types.BooleanPreference):
    # Boolean are supported in JSON, so no need to serialized to a string
    serializer = None


class IntSetting(types.IntegerPreference):
    # Integers are supported in JSON, so no need to serialized to a string
    serializer = None


def validate_config(payload, settings):
    """
    Dynamic preferences stores settings in a separate database table. However
    it is a bit too much for our use cases, and we simply want to store
    these in a JSONField on the corresponding model row.

    This validates the payload using the dynamic preferences serializers
    and return a config that is ready to be persisted as JSON
    """
    final = {}

    for klass in settings:
        setting = klass()
        setting_id = setting.identifier()
        try:
            value = payload[setting_id]
        except KeyError:
            continue

        setting.validate(value)
        if setting.serializer:
            value = setting.serializer.serialize(value)
        final[setting_id] = value
    return final

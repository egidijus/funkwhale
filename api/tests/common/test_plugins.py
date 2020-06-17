import pytest

from rest_framework import serializers

from config import plugins
from funkwhale_api.common import models


def test_plugin_validate_set_conf():
    class S(serializers.Serializer):
        test = serializers.CharField()
        foo = serializers.BooleanField()

    class P(plugins.Plugin):
        conf_serializer = S

    p = P("noop", "noop")
    with pytest.raises(serializers.ValidationError):
        assert p.set_conf({"test": "hello", "foo": "bar"})


def test_plugin_validate_set_conf_persists():
    class S(serializers.Serializer):
        test = serializers.CharField()
        foo = serializers.BooleanField()

    class P(plugins.Plugin):
        name = "test_plugin"
        conf_serializer = S

    p = P("noop", "noop")
    p.set_conf({"test": "hello", "foo": False})
    assert p.instance() == models.PodPlugin.objects.latest("id")
    assert p.instance().conf == {"test": "hello", "foo": False}

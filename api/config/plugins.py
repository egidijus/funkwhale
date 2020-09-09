import copy
import logging
import os
import subprocess
import sys

import persisting_theory
from django.core.cache import cache
from django.db.models import Q

from rest_framework import serializers

logger = logging.getLogger("plugins")


class Startup(persisting_theory.Registry):
    look_into = "persisting_theory"


class Ready(persisting_theory.Registry):
    look_into = "persisting_theory"


startup = Startup()
ready = Ready()

_plugins = {}
_filters = {}
_hooks = {}


class PluginCache(object):
    def __init__(self, prefix):
        self.prefix = prefix

    def get(self, key, default=None):
        key = ":".join([self.prefix, key])
        return cache.get(key, default)

    def set(self, key, value, duration=None):
        key = ":".join([self.prefix, key])
        return cache.set(key, value, duration)


def get_plugin_config(
    name,
    user=False,
    source=False,
    registry=_plugins,
    conf={},
    settings={},
    description=None,
    version=None,
    label=None,
    homepage=None,
):
    conf = {
        "name": name,
        "label": label or name,
        "logger": logger,
        # conf is for dynamic settings
        "conf": conf,
        # settings is for settings hardcoded in .env
        "settings": settings,
        "user": True if source else user,
        # source plugins are plugins that provide audio content
        "source": source,
        "description": description,
        "version": version,
        "cache": PluginCache(name),
        "homepage": homepage,
    }
    registry[name] = conf
    return conf


def load_settings(name, settings):
    from django.conf import settings as django_settings

    mapping = {
        "boolean": django_settings.ENV.bool,
        "text": django_settings.ENV,
    }
    values = {}
    prefix = "FUNKWHALE_PLUGIN_{}".format(name.upper())
    for s in settings:
        key = "_".join([prefix, s["name"].upper()])
        value = mapping[s["type"]](key, default=s.get("default", None))
        values[s["name"]] = value

    logger.debug("Plugin %s running with settings %s", name, values)
    return values


def get_session():
    from funkwhale_api.common import session

    return session.get_session()


def register_filter(name, plugin_config, registry=_filters):
    def decorator(func):
        handlers = registry.setdefault(name, [])

        def inner(*args, **kwargs):
            plugin_config["logger"].debug("Calling filter for %s", name)
            rval = func(*args, **kwargs)
            return rval

        handlers.append((plugin_config["name"], inner))
        return inner

    return decorator


def register_hook(name, plugin_config, registry=_hooks):
    def decorator(func):
        handlers = registry.setdefault(name, [])

        def inner(*args, **kwargs):
            plugin_config["logger"].debug("Calling hook for %s", name)
            func(*args, **kwargs)

        handlers.append((plugin_config["name"], inner))
        return inner

    return decorator


class Skip(Exception):
    pass


def trigger_filter(name, value, enabled=False, **kwargs):
    """
    Call filters registered for "name" with the given
    args and kwargs.

    Return the value (that could be modified by handlers)
    """
    logger.debug("Calling handlers for filter %s", name)
    registry = kwargs.pop("registry", _filters)
    confs = kwargs.pop("confs", {})
    for plugin_name, handler in registry.get(name, []):
        if not enabled and confs.get(plugin_name, {}).get("enabled") is False:
            continue
        try:
            value = handler(value, conf=confs.get(plugin_name, {}), **kwargs)
        except Skip:
            pass
        except Exception as e:
            logger.warn("Plugin %s errored during filter %s: %s", plugin_name, name, e)
    return value


def trigger_hook(name, enabled=False, **kwargs):
    """
    Call hooks registered for "name" with the given
    args and kwargs.

    Returns nothing
    """
    logger.debug("Calling handlers for hook %s", name)
    registry = kwargs.pop("registry", _hooks)
    confs = kwargs.pop("confs", {})
    for plugin_name, handler in registry.get(name, []):
        if not enabled and confs.get(plugin_name, {}).get("enabled") is False:
            continue
        try:
            handler(conf=confs.get(plugin_name, {}).get("conf"), **kwargs)
        except Skip:
            pass
        except Exception as e:
            logger.warn("Plugin %s errored during hook %s: %s", plugin_name, name, e)


def set_conf(name, conf, user=None, registry=_plugins):
    from funkwhale_api.common import models

    if not registry[name]["conf"] and not registry[name]["source"]:
        return
    conf_serializer = get_serializer_from_conf_template(
        registry[name]["conf"], user=user, source=registry[name]["source"],
    )(data=conf)
    conf_serializer.is_valid(raise_exception=True)
    if "library" in conf_serializer.validated_data:
        conf_serializer.validated_data["library"] = str(
            conf_serializer.validated_data["library"]
        )
    conf, _ = models.PluginConfiguration.objects.update_or_create(
        user=user, code=name, defaults={"conf": conf_serializer.validated_data}
    )


def get_confs(user=None):
    from funkwhale_api.common import models

    qs = models.PluginConfiguration.objects.filter(code__in=list(_plugins.keys()))
    if user:
        qs = qs.filter(Q(user=None) | Q(user=user))
    else:
        qs = qs.filter(user=None)
    confs = {
        v["code"]: {"conf": v["conf"], "enabled": v["enabled"]}
        for v in qs.values("code", "conf", "enabled")
    }
    for p, v in _plugins.items():
        if p not in confs:
            confs[p] = {"conf": None, "enabled": False}
    return confs


def get_conf(plugin, user=None):
    return get_confs(user=user)[plugin]


def enable_conf(code, value, user):
    from funkwhale_api.common import models

    models.PluginConfiguration.objects.update_or_create(
        code=code, user=user, defaults={"enabled": value}
    )


class LibraryField(serializers.UUIDField):
    def __init__(self, *args, **kwargs):
        self.actor = kwargs.pop("actor")
        super().__init__(*args, **kwargs)

    def to_internal_value(self, v):
        v = super().to_internal_value(v)
        if not self.actor.libraries.filter(uuid=v).first():
            raise serializers.ValidationError("Invalid library id")
        return v


def get_serializer_from_conf_template(conf, source=False, user=None):
    conf = copy.deepcopy(conf)
    validators = {f["name"]: f.pop("validator") for f in conf if "validator" in f}
    mapping = {
        "url": serializers.URLField,
        "boolean": serializers.BooleanField,
        "text": serializers.CharField,
        "long_text": serializers.CharField,
        "password": serializers.CharField,
        "number": serializers.IntegerField,
    }

    for attr in ["label", "help"]:
        for c in conf:
            c.pop(attr, None)

    class Serializer(serializers.Serializer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for field_conf in conf:
                field_kwargs = copy.copy(field_conf)
                name = field_kwargs.pop("name")
                self.fields[name] = mapping[field_kwargs.pop("type")](**field_kwargs)
            if source:
                self.fields["library"] = LibraryField(actor=user.actor)

    for vname, v in validators.items():
        setattr(Serializer, "validate_{}".format(vname), v)
    return Serializer


def serialize_plugin(plugin_conf, confs):
    return {
        "name": plugin_conf["name"],
        "label": plugin_conf["label"],
        "description": plugin_conf.get("description") or None,
        "user": plugin_conf.get("user", False),
        "source": plugin_conf.get("source", False),
        "conf": plugin_conf.get("conf", None),
        "values": confs.get(plugin_conf["name"], {"conf"}).get("conf"),
        "enabled": plugin_conf["name"] in confs
        and confs[plugin_conf["name"]]["enabled"],
        "homepage": plugin_conf["homepage"],
    }


def install_dependencies(deps):
    if not deps:
        return
    logger.info("Installing plugins dependencies %s", deps)
    pip_path = os.path.join(os.path.dirname(sys.executable), "pip")
    subprocess.check_call([pip_path, "install"] + deps)


def background_task(name):
    from funkwhale_api.taskapp import celery

    def decorator(func):
        return celery.app.task(func, name=name)

    return decorator


# HOOKS
LISTENING_CREATED = "listening_created"
"""
Called when a track is being listened
"""
SCAN = "scan"
"""

"""
# FILTERS
PLUGINS_DEPENDENCIES = "plugins_dependencies"
"""
Called with an empty list, use this filter to append pip dependencies
to the list for installation.
"""
PLUGINS_APPS = "plugins_apps"
"""
Called with an empty list, use this filter to append apps to INSTALLED_APPS
"""
MIDDLEWARES_BEFORE = "middlewares_before"
"""
Called with an empty list, use this filter to prepend middlewares
to MIDDLEWARE
"""
MIDDLEWARES_AFTER = "middlewares_after"
"""
Called with an empty list, use this filter to append middlewares
to MIDDLEWARE
"""
URLS = "urls"
"""
Called with an empty list, use this filter to register new urls and views
"""

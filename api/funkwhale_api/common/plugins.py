import logging
import persisting_theory
from django.apps import AppConfig


logger = logging.getLogger("funkwhale.plugins")


class PluginsRegistry(persisting_theory.Registry):
    look_into = "hooks"

    def prepare_name(self, data, name=None):
        return data.name

    def prepare_data(self, data):
        data.plugins_registry = self
        return data

    def dispatch_action(self, action_name, **kwargs):
        logger.debug("Dispatching plugin action %s", action_name)
        for plugin in self.values():
            try:
                handler = plugin.hooked_actions[action_name]
            except KeyError:
                continue

            logger.debug("Hook found for plugin %s", plugin.name)
            try:
                handler(plugin=plugin, **kwargs)
            except Exception:
                logger.exception(
                    "Hook for action %s from plugin %s failed. The plugin may be misconfigured.",
                    action_name,
                    plugin.name,
                )
            else:
                logger.info(
                    "Hook for action %s from plugin %s successful",
                    action_name,
                    plugin.name,
                )


registry = PluginsRegistry()


class Plugin(AppConfig):
    _is_funkwhale_plugin = True
    is_initialized = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = {}
        self.hooked_actions = {}

    def get_config(self, config):
        """
        Called with config options extracted from env vars, if any specified
        Returns a transformed dict
        """
        return config

    def set_config(self, config):
        """
        Simply persist the given config on the plugin
        """
        self.config = config

    def initialize(self):
        pass

    def register_action(self, action_name, func):
        logger.debug(
            "Registered hook for action %s via plugin %s", action_name, self.name
        )
        self.hooked_actions[action_name] = func


def init(registry, plugins):
    logger.debug("Initializing plugins...")
    for plugin in plugins:
        logger.info("Initializing plugin %s", plugin.name)
        try:
            config = plugin.get_config({})
        except Exception:
            logger.exception(
                "Error while getting configuration, plugin %s disabled", plugin.name
            )
            continue

        try:
            plugin.set_config(config)
        except Exception:
            logger.exception(
                "Error while setting configuration, plugin %s disabled", plugin.name
            )
            continue

        try:
            plugin.initialize()
        except Exception:
            logger.exception(
                "Error while initializing, plugin %s disabled", plugin.name
            )
            continue

        plugin.is_initialized = True

    # initialization complete, now we can log the "hooks.py" file in each
    # plugin directory
    registry.autodiscover([p.name for p in plugins if p.is_initialized])

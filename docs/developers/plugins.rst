Funkwhale plugins
=================

Starting with Funkwhale 1.0, it is now possible to implement new features
via plugins. 

Some plugins are maintained by the Funkwhale team (e.g. this is the case of the ``scrobbler`` plugin),
or by third-parties.

Installing a plugin
-------------------

To install a plugin, ensure its directory is present in the ``FUNKWHALE_PLUGINS_PATH`` directory.

Then, add its name to the ``FUNKWHALE_PLUGINS`` environment variable, like this::

    FUNKWHALE_PLUGINS=myplugin,anotherplugin

We provide a command to make it easy to install third-party plugins::

    python manage.py fw plugins install https://pluginurl.zip

.. note::

    If you use the command, you will still need to append the plugin name to ``FUNKWHALE_PLUGINS``


Types of plugins
----------------

There are two types of plugins:

1. Plugins that are accessible to end-users, a.k.a. user-level plugins. This is the case of our Scrobbler plugin
2. Pod-level plugins that are configured by pod admins and are not tied to a particular user

Additionally, user-level plugins can be regular plugins or source plugins. A source plugin provides
a way to import files from a third-party service, e.g via webdav, FTP or something similar.

Hooks and filters
-----------------

Funkwhale includes two kind of entrypoints for plugins to use: hooks and filters. B

Hooks should be used when you want to react to some change. For instance, the ``LISTENING_CREATED`` hook
notify each registered callback that a listening was created. Our ``scrobbler`` plugin has a callback
registered to this hook, so that it can notify Last.fm properly:

.. code-block:: python

    from config import plugins
    from .funkwhale_startup import PLUGIN

    @plugins.register_hook(plugins.LISTENING_CREATED, PLUGIN)
    def notify_lastfm(listening, conf, **kwargs):
        # do something

Filters work slightly differently, and expect callbacks to return a value that will be used by Funkwhale.

For instance, the ``PLUGINS_DEPENDENCIES`` filter can be used as a way to install additional dependencies needed by your plugin:


.. code-block:: python

    # funkwhale_startup.py
    # ...
    from config import plugins

    @plugins.register_filter(plugins.PLUGINS_DEPENDENCIES, PLUGIN)
    def dependencies(dependencies, **kwargs):
        return dependencies + ["django_prometheus"]

To sum it up, hooks are used when you need to react to something, and filters when you need to alter something.

Writing a plugin
----------------

Regardless of the type of plugin you want to write, lots of concepts are similar.

First, a plugin need three files:

- a ``__init__.py`` file, since it's a Python package
- a ``funkwhale_startup.py`` file, that is loaded during Funkwhale initialization
- a ``funkwhale_ready.py`` file, that is loaded when Funkwhale is configured and ready 

So your plugin directory should look like this::

    myplugin
    ├── funkwhale_ready.py
    ├── funkwhale_startup.py
    └── __init__.py

Now, let's write our plugin!

``funkwhale_startup.py`` is where you declare your plugin and it's configuration options:

.. code-block:: python

    # funkwhale_startup.py
    from config import plugins

    PLUGIN = plugins.get_plugin_config(
        name="myplugin",
        label="My Plugin",
        description="An example plugin that greets you",
        version="0.1",
        # here, we write a user-level plugin
        user=True,
        conf=[
            # this configuration options are editable by each user
            {"name": "greeting", "type": "text", "label": "Greeting", "default": "Hello"},
        ],
    )

Now that our plugin is declared and configured, let's implement actual functionality in ``funkwhale_ready.py``:

.. code-block:: python

    # funkwhale_ready.py
    from django.urls import path
    from rest_framework import response
    from rest_framework import views

    from config import plugins

    from .funkwhale_startup import PLUGIN

    # Our greeting view, where the magic happens
    class GreetingView(views.APIView):
        permission_classes = []
        def get(self, request, *args, **kwargs):
            # retrieve plugin configuration for the current user
            conf = plugins.get_conf(PLUGIN["name"], request.user)
            if not conf["enabled"]:
                # plugin is disabled for this user
                return response.Response(status=405)
            greeting = conf["conf"]["greeting"]
            data = {
                "greeting": "{} {}!".format(greeting, request.user.username)
            }
            return response.Response(data)

    # Ensure our view is known by Django and available at /greeting
    @plugins.register_filter(plugins.URLS, PLUGIN)
    def register_view(urls, **kwargs):
        return urls + [
            path('greeting', GreetingView.as_view())
        ]

And that's pretty much it. Now, login, visit https://yourpod.domain/settings/plugins, set a value in the ``greeting`` field and enable the plugin.

After that, you should be greeted properly if you go to https://yourpod.domain/greeting.

Hooks reference
---------------

.. autodata:: config.plugins.LISTENING_CREATED

Filters reference
-----------------

.. autodata:: config.plugins.PLUGINS_DEPENDENCIES
.. autodata:: config.plugins.PLUGINS_APPS
.. autodata:: config.plugins.PLUGINSMIDDLEWARES_BEFORE_DEPENDENCIES
.. autodata:: config.plugins.MIDDLEWARES_AFTER
.. autodata:: config.plugins.URLS

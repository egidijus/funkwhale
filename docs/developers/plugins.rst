Funkwhale Plugins
=================

With version 1.0, Funkwhale makes it possible for third party to write plugins
and distribute them.

Funkwhale plugins are regular django apps, that can register models, API
endpoints, and react to specific events (e.g a son was listened, a federation message was delivered, etc.)

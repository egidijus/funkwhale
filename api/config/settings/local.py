# -*- coding: utf-8 -*-
"""
Local settings

- Run in Debug mode
- Use console backend for emails
- Add Django Debug Toolbar
- Add django-extensions as app
"""

from .common import *  # noqa


# DEBUG
# ------------------------------------------------------------------------------
DEBUG = env.bool("DJANGO_DEBUG", default=True)
FORCE_HTTPS_URLS = env.bool("FORCE_HTTPS_URLS", default=False)
TEMPLATES[0]["OPTIONS"]["debug"] = DEBUG

# Mail settings
# ------------------------------------------------------------------------------
EMAIL_HOST = "localhost"
EMAIL_PORT = 1025

# django-debug-toolbar
# ------------------------------------------------------------------------------

# INTERNAL_IPS = ('127.0.0.1', '10.0.2.2',)

DEBUG_TOOLBAR_CONFIG = {
    "DISABLE_PANELS": ["debug_toolbar.panels.redirects.RedirectsPanel"],
    "SHOW_TEMPLATE_CONTEXT": True,
    "SHOW_TOOLBAR_CALLBACK": lambda request: "debug" in request.GET,
    "JQUERY_URL": "/staticfiles/admin/js/vendor/jquery/jquery.js",
}
# DEBUG_TOOLBAR_PANELS = [
#     'debug_toolbar.panels.versions.VersionsPanel',
#     'debug_toolbar.panels.timer.TimerPanel',
#     'debug_toolbar.panels.settings.SettingsPanel',
#     'debug_toolbar.panels.headers.HeadersPanel',
#     'debug_toolbar.panels.request.RequestPanel',
#     'debug_toolbar.panels.sql.SQLPanel',
#     'debug_toolbar.panels.staticfiles.StaticFilesPanel',
#     'debug_toolbar.panels.templates.TemplatesPanel',
#     'debug_toolbar.panels.cache.CachePanel',
#     'debug_toolbar.panels.signals.SignalsPanel',
#     'debug_toolbar.panels.logging.LoggingPanel',
#     'debug_toolbar.panels.redirects.RedirectsPanel',
#     'debug_toolbar.panels.profiling.ProfilingPanel',
#     'debug_toolbar_line_profiler.panel.ProfilingPanel'
# ]

DEBUG_TOOLBAR_PANELS = [
    # 'debug_toolbar.panels.versions.VersionsPanel',
    "debug_toolbar.panels.timer.TimerPanel",
    "debug_toolbar.panels.settings.SettingsPanel",
    "debug_toolbar.panels.headers.HeadersPanel",
    # 'debug_toolbar.panels.request.RequestPanel',
    "debug_toolbar.panels.sql.SQLPanel",
    # 'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    # 'debug_toolbar.panels.templates.TemplatesPanel',
    "debug_toolbar.panels.cache.CachePanel",
    # 'debug_toolbar.panels.signals.SignalsPanel',
    # 'debug_toolbar.panels.logging.LoggingPanel',
    # 'debug_toolbar.panels.redirects.RedirectsPanel',
    # 'debug_toolbar.panels.profiling.ProfilingPanel',
]

# django-extensions
# ------------------------------------------------------------------------------
# INSTALLED_APPS += ('django_extensions', )

# Debug toolbar is slow, we disable it for tests
DEBUG_TOOLBAR_ENABLED = env.bool("DEBUG_TOOLBAR_ENABLED", default=DEBUG)
if DEBUG_TOOLBAR_ENABLED:
    MIDDLEWARE += ("debug_toolbar.middleware.DebugToolbarMiddleware",)
    INSTALLED_APPS += ("debug_toolbar",)

# TESTING
# ------------------------------------------------------------------------------
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# CELERY
CELERY_TASK_ALWAYS_EAGER = False
# END CELERY

# Your local stuff: Below this line define 3rd party library settings

CSRF_TRUSTED_ORIGINS = [o for o in ALLOWED_HOSTS]


if env.bool("WEAK_PASSWORDS", default=False):
    # Faster during tests
    PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)

MIDDLEWARE = (
    "funkwhale_api.common.middleware.DevHttpsMiddleware",
    "funkwhale_api.common.middleware.ProfilerMiddleware",
) + MIDDLEWARE

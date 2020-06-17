# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import datetime
import logging.config
import os
import sys

import persisting_theory

from urllib.parse import urlsplit
from celery.schedules import crontab
from funkwhale_api import __version__
import environ

ROOT_DIR = environ.Path(__file__) - 3  # (/a/b/myfile.py - 3 = /)
APPS_DIR = ROOT_DIR.path("funkwhale_api")
sys.path.append(os.path.join(APPS_DIR, "plugins"))
logger = logging.getLogger("funkwhale_api.config")
env = environ.Env()


class Plugins(persisting_theory.Registry):
    look_into = "entrypoint"


PLUGINS = [p for p in env.list("FUNKWHALE_PLUGINS", default=[]) if p]
"""
List of Funkwhale plugins to load.
"""
from config import plugins  # noqa

plugins_registry = Plugins()
plugins_registry.autodiscover(PLUGINS)

# plugins.plugins_manager.register(Plugin("noop", "noop"))

LOGLEVEL = env("LOGLEVEL", default="info").upper()
"""
Default logging level for the Funkwhale processes"""  # pylint: disable=W0105

LOGGING_CONFIG = None
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "console": {"format": "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"}
        },
        "handlers": {
            "console": {"class": "logging.StreamHandler", "formatter": "console"},
            # # Add Handler for Sentry for `warning` and above
            # 'sentry': {
            #     'level': 'WARNING',
            #     'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
            # },
        },
        "loggers": {
            "funkwhale_api": {
                "level": LOGLEVEL,
                "handlers": ["console"],
                # required to avoid double logging with root logger
                "propagate": False,
            },
            "": {"level": "WARNING", "handlers": ["console"]},
        },
    }
)

ENV_FILE = env_file = env("ENV_FILE", default=None)
"""
Path to a .env file to load
"""
if env_file:
    logger.info("Loading specified env file at %s", env_file)
    # we have an explicitely specified env file
    # so we try to load and it fail loudly if it does not exist
    env.read_env(env_file)
else:
    # we try to load from .env and config/.env
    # but do not crash if those files don't exist
    paths = [
        # /srv/funwhale/api/.env
        ROOT_DIR,
        # /srv/funwhale/config/.env
        ((ROOT_DIR - 1) + "config"),
    ]
    for path in paths:
        try:
            env_path = path.file(".env")
        except FileNotFoundError:
            logger.debug("No env file found at %s/.env", path)
            continue
        env.read_env(env_path)
        logger.info("Loaded env file at %s/.env", path)
        break

FUNKWHALE_PLUGINS_PATH = env(
    "FUNKWHALE_PLUGINS_PATH", default="/srv/funkwhale/plugins/"
)
"""
Path to a directory containing Funkwhale plugins. These will be imported at runtime.
"""
sys.path.append(FUNKWHALE_PLUGINS_PATH)

FUNKWHALE_HOSTNAME = None
FUNKWHALE_HOSTNAME_SUFFIX = env("FUNKWHALE_HOSTNAME_SUFFIX", default=None)
FUNKWHALE_HOSTNAME_PREFIX = env("FUNKWHALE_HOSTNAME_PREFIX", default=None)
if FUNKWHALE_HOSTNAME_PREFIX and FUNKWHALE_HOSTNAME_SUFFIX:
    # We're in traefik case, in development
    FUNKWHALE_HOSTNAME = "{}.{}".format(
        FUNKWHALE_HOSTNAME_PREFIX, FUNKWHALE_HOSTNAME_SUFFIX
    )
    FUNKWHALE_PROTOCOL = env("FUNKWHALE_PROTOCOL", default="https")
else:
    try:
        FUNKWHALE_HOSTNAME = env("FUNKWHALE_HOSTNAME")
        """
        Hostname of your Funkwhale pod, e.g ``mypod.audio``
        """

        FUNKWHALE_PROTOCOL = env("FUNKWHALE_PROTOCOL", default="https")
        """
        Protocol end users will use to access your pod, either ``http`` or ``https``.
        """
    except Exception:
        FUNKWHALE_URL = env("FUNKWHALE_URL")
        _parsed = urlsplit(FUNKWHALE_URL)
        FUNKWHALE_HOSTNAME = _parsed.netloc
        FUNKWHALE_PROTOCOL = _parsed.scheme

FUNKWHALE_PROTOCOL = FUNKWHALE_PROTOCOL.lower()
FUNKWHALE_HOSTNAME = FUNKWHALE_HOSTNAME.lower()
FUNKWHALE_URL = "{}://{}".format(FUNKWHALE_PROTOCOL, FUNKWHALE_HOSTNAME)
FUNKWHALE_SPA_HTML_ROOT = env(
    "FUNKWHALE_SPA_HTML_ROOT", default=FUNKWHALE_URL + "/front/"
)
"""
URL or path to the Web Application files. Funkwhale needs access to it so that
it can inject <meta> tags relevant to the given page (e.g page title, cover, etc.).

If a URL is specified, the index.html file will be fetched through HTTP. If a path is provided,
it will be accessed from disk.

Use something like ``/srv/funkwhale/front/dist/`` if the web processes shows request errors related to this.
"""

FUNKWHALE_SPA_HTML_CACHE_DURATION = env.int(
    "FUNKWHALE_SPA_HTML_CACHE_DURATION", default=60 * 15
)
FUNKWHALE_EMBED_URL = env(
    "FUNKWHALE_EMBED_URL", default=FUNKWHALE_URL + "/front/embed.html"
)
FUNKWHALE_SPA_REWRITE_MANIFEST = env.bool(
    "FUNKWHALE_SPA_REWRITE_MANIFEST", default=True
)
FUNKWHALE_SPA_REWRITE_MANIFEST_URL = env.bool(
    "FUNKWHALE_SPA_REWRITE_MANIFEST_URL", default=None
)

APP_NAME = "Funkwhale"

# XXX: for backward compat with django 2.2, remove this when django 2.2 support is dropped
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = env.bool(
    "DJANGO_ALLOW_ASYNC_UNSAFE", default="true"
)

# XXX: deprecated, see #186
FEDERATION_ENABLED = env.bool("FEDERATION_ENABLED", default=True)
FEDERATION_HOSTNAME = env("FEDERATION_HOSTNAME", default=FUNKWHALE_HOSTNAME).lower()
# XXX: deprecated, see #186
FEDERATION_COLLECTION_PAGE_SIZE = env.int("FEDERATION_COLLECTION_PAGE_SIZE", default=50)
# XXX: deprecated, see #186
FEDERATION_MUSIC_NEEDS_APPROVAL = env.bool(
    "FEDERATION_MUSIC_NEEDS_APPROVAL", default=True
)
# XXX: deprecated, see #186
FEDERATION_ACTOR_FETCH_DELAY = env.int("FEDERATION_ACTOR_FETCH_DELAY", default=60 * 12)
FEDERATION_SERVICE_ACTOR_USERNAME = env(
    "FEDERATION_SERVICE_ACTOR_USERNAME", default="service"
)
# How many pages to fetch when crawling outboxes and third-party collections
FEDERATION_COLLECTION_MAX_PAGES = env.int("FEDERATION_COLLECTION_MAX_PAGES", default=5)
"""
Number of existing pages of content to fetch when discovering/refreshing an actor or channel.

More pages means more content will be loaded, but will require more resources.
"""

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[]) + [FUNKWHALE_HOSTNAME]
"""
List of allowed hostnames for which the Funkwhale server will answer.
"""

# APP CONFIGURATION
# ------------------------------------------------------------------------------
DJANGO_APPS = (
    "channels",
    # Default Django apps:
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # Useful template tags:
    # 'django.contrib.humanize',
    # Admin
    "django.contrib.admin",
)
THIRD_PARTY_APPS = (
    # 'crispy_forms',  # Form layouts
    "allauth",  # registration
    "allauth.account",  # registration
    "allauth.socialaccount",  # registration
    "corsheaders",
    "oauth2_provider",
    "rest_framework",
    "rest_framework.authtoken",
    "rest_auth",
    "rest_auth.registration",
    "dynamic_preferences",
    "django_filters",
    "django_cleanup",
    "versatileimagefield",
)


# Sentry
RAVEN_ENABLED = env.bool("RAVEN_ENABLED", default=False)
RAVEN_DSN = env("RAVEN_DSN", default="")

if RAVEN_ENABLED:
    RAVEN_CONFIG = {
        "dsn": RAVEN_DSN,
        # If you are using git, you can also automatically configure the
        # release based on the git info.
        "release": __version__,
    }
    THIRD_PARTY_APPS += ("raven.contrib.django.raven_compat",)

# Apps specific for this project go here.
LOCAL_APPS = (
    "funkwhale_api.common.apps.CommonConfig",
    "funkwhale_api.activity.apps.ActivityConfig",
    "funkwhale_api.users",  # custom users app
    "funkwhale_api.users.oauth",
    # Your stuff: custom apps go here
    "funkwhale_api.instance",
    "funkwhale_api.audio",
    "funkwhale_api.music",
    "funkwhale_api.requests",
    "funkwhale_api.favorites",
    "funkwhale_api.federation",
    "funkwhale_api.moderation.apps.ModerationConfig",
    "funkwhale_api.radios",
    "funkwhale_api.history",
    "funkwhale_api.playlists",
    "funkwhale_api.subsonic",
    "funkwhale_api.tags",
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps


ADDITIONAL_APPS = env.list("ADDITIONAL_APPS", default=[])
"""
List of Django apps to load in addition to Funkwhale plugins and apps.
"""

PLUGINS_APPS = tuple()

for p in plugins.trigger_hook("register_apps"):
    PLUGINS_APPS += (p,)

INSTALLED_APPS = (
    DJANGO_APPS
    + THIRD_PARTY_APPS
    + LOCAL_APPS
    + tuple(ADDITIONAL_APPS)
    + tuple(PLUGINS)
    + tuple(PLUGINS_APPS)
)

if PLUGINS:
    logger.info("Running with the following plugins enabled: %s", ", ".join(PLUGINS))
else:
    logger.info("Running with no plugins")

# MIDDLEWARE CONFIGURATION
# ------------------------------------------------------------------------------
ADDITIONAL_MIDDLEWARES_START = env.list("ADDITIONAL_MIDDLEWARES_START", default=[])
for group in plugins.trigger_hook("middlewares_before"):
    for m in group:
        ADDITIONAL_MIDDLEWARES_START.append(m)

ADDITIONAL_MIDDLEWARES_END = env.list("ADDITIONAL_MIDDLEWARES_END", default=[])
for group in plugins.trigger_hook("middlewares_after"):
    for m in group:
        ADDITIONAL_MIDDLEWARES_END.append(m)

MIDDLEWARE = (
    tuple(ADDITIONAL_MIDDLEWARES_START)
    + (
        "django.middleware.security.SecurityMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
        "corsheaders.middleware.CorsMiddleware",
        # needs to be before SPA middleware
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        # /end
        "funkwhale_api.common.middleware.SPAFallbackMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "funkwhale_api.users.middleware.RecordActivityMiddleware",
        "funkwhale_api.common.middleware.ThrottleStatusMiddleware",
    )
    + tuple(ADDITIONAL_MIDDLEWARES_END)
)


# DEBUG
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DJANGO_DEBUG = DEBUG = env.bool("DJANGO_DEBUG", False)
"""
Whether to enable debugging info and pages. Never enable this on a production server,
as it can leak very sensitive information.
"""
# FIXTURE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS
FIXTURE_DIRS = (str(APPS_DIR.path("fixtures")),)

# EMAIL CONFIGURATION
# ------------------------------------------------------------------------------

# EMAIL
# ------------------------------------------------------------------------------
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL", default="Funkwhale <noreply@{}>".format(FUNKWHALE_HOSTNAME)
)
"""
Name and email address used to send system emails.

Default: ``Funkwhale <noreply@yourdomain>``

.. note::

    Both the forms ``Funkwhale <noreply@yourdomain>`` and
    ``noreply@yourdomain`` work.

"""
EMAIL_SUBJECT_PREFIX = env("EMAIL_SUBJECT_PREFIX", default="[Funkwhale] ")
"""
Subject prefix for system emails.
"""
SERVER_EMAIL = env("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)


EMAIL_CONFIG = env.email_url("EMAIL_CONFIG", default="consolemail://")
"""
SMTP configuration for sending emails. Possible values:

- ``EMAIL_CONFIG=consolemail://``: output emails to console (the default)
- ``EMAIL_CONFIG=dummymail://``: disable email sending completely

On a production instance, you'll usually want to use an external SMTP server:

- ``EMAIL_CONFIG=smtp://user@:password@youremail.host:25``
- ``EMAIL_CONFIG=smtp+ssl://user@:password@youremail.host:465``
- ``EMAIL_CONFIG=smtp+tls://user@:password@youremail.host:587``

.. note::

    If ``user`` or ``password`` contain special characters (eg.
    ``noreply@youremail.host`` as ``user``), be sure to urlencode them, using
    for example the command:
    ``python3 -c 'import urllib.parse; print(urllib.parse.quote_plus("noreply@youremail.host"))'``
    (returns ``noreply%40youremail.host``)

"""
vars().update(EMAIL_CONFIG)

# DATABASE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASE_URL = env.db("DATABASE_URL")
"""
URL to connect to the PostgreSQL database. Examples:

- ``postgresql://funkwhale@:5432/funkwhale``
- ``postgresql://<user>:<password>@<host>:<port>/<database>``
- ``postgresql://funkwhale:passw0rd@localhost:5432/funkwhale_database``
"""
DATABASES = {
    # Raises ImproperlyConfigured exception if DATABASE_URL not in os.environ
    "default": DATABASE_URL
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DB_CONN_MAX_AGE = DATABASES["default"]["CONN_MAX_AGE"] = env(
    "DB_CONN_MAX_AGE", default=60 * 5
)

engine = plugins.trigger_hook("database_engine")[-1]
DATABASES["default"]["ENGINE"] = engine
"""
Max time, in seconds, before database connections are closed.
"""
MIGRATION_MODULES = {
    # see https://github.com/jazzband/django-oauth-toolkit/issues/634
    # swappable models are badly designed in oauth2_provider
    # ignore migrations and provide our own models.
    "oauth2_provider": None,
    "sites": "funkwhale_api.contrib.sites.migrations",
}

# GENERAL CONFIGURATION
# ------------------------------------------------------------------------------
# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = "UTC"

# See: https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"

# See: https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True

# TEMPLATE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        "DIRS": [str(APPS_DIR.path("templates"))],
        "OPTIONS": {
            # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
            "debug": DEBUG,
            # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
            # https://docs.djangoproject.com/en/dev/ref/templates/api/#loader-types
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
            # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                # Your stuff: custom template context processors go here
            ],
        },
    }
]

# See: http://django-crispy-forms.readthedocs.org/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = "bootstrap3"

# STATIC FILE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = env("STATIC_ROOT", default=str(ROOT_DIR("staticfiles")))
"""
Path were static files should be collected.
"""
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = env("STATIC_URL", default=FUNKWHALE_URL + "/staticfiles/")
DEFAULT_FILE_STORAGE = "funkwhale_api.common.storage.ASCIIFileSystemStorage"

PROXY_MEDIA = env.bool("PROXY_MEDIA", default=True)
"""
Wether to proxy audio files through your reverse proxy. It's recommended to keep this on,
as a way to enforce access control, however, if you're using S3 storage with :attr:`AWS_QUERYSTRING_AUTH`,
it's safe to disable it.
"""
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = env.bool("AWS_QUERYSTRING_AUTH", default=not PROXY_MEDIA)
"""
Whether to include signatures in S3 urls, as a way to enforce access-control.

Defaults to the inverse of :attr:`PROXY_MEDIA`.
"""

AWS_S3_MAX_MEMORY_SIZE = env.int(
    "AWS_S3_MAX_MEMORY_SIZE", default=1000 * 1000 * 1000 * 20
)

AWS_QUERYSTRING_EXPIRE = env.int("AWS_QUERYSTRING_EXPIRE", default=3600)
"""
Expiration delay, in seconds, of signatures generated when :attr:`AWS_QUERYSTRING_AUTH` is enabled.
"""

AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default=None)
"""
Access-key ID for your S3 storage.
"""
SECRET_KEY = env("DJANGO_SECRET_KEY")

if AWS_ACCESS_KEY_ID:
    AWS_ACCESS_KEY_ID = AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    """
    Secret access key for your S3 storage.
    """
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    """
    Bucket name of your S3 storage.
    """
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default=None)
    """
    Custom domain to use for your S3 storage.
    """
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)
    """
    If you use a S3-compatible storage such as minio, set the following variable to
    the full URL to the storage server. Example:

    - ``https://minio.mydomain.com``
    - ``https://s3.wasabisys.com``
    """
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default=None)
    """If you are using Amazon S3 to serve media directly, you will need to specify your region
    name in order to access files. Example:

    - ``eu-west-2``
    """

    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_LOCATION = env("AWS_LOCATION", default="")
    """
    An optional bucket subdirectory were you want to store the files. This is especially useful
    if you plan to use share the bucket with other services
    """
    DEFAULT_FILE_STORAGE = "funkwhale_api.common.storage.ASCIIS3Boto3Storage"


# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = (str(APPS_DIR.path("static")),)

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)

# MEDIA CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = env("MEDIA_ROOT", default=str(APPS_DIR("media")))
"""
Where media files (such as album covers or audio tracks) should be stored
on your system? (Ensure this directory actually exists)
"""
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = env("MEDIA_URL", default=FUNKWHALE_URL + "/media/")
"""
URL where media files are served. The default value should work fine on most
configurations, but could can tweak this if you are hosting media files on a separate
domain, or if you host Funkwhale on a non-standard port.
"""
FILE_UPLOAD_PERMISSIONS = 0o644

ATTACHMENTS_UNATTACHED_PRUNE_DELAY = env.int(
    "ATTACHMENTS_UNATTACHED_PRUNE_DELAY", default=3600 * 24
)
"""
Delay in seconds before uploaded but unattached attachements are pruned from the system.
"""

# URL Configuration
# ------------------------------------------------------------------------------
ROOT_URLCONF = "config.urls"
SPA_URLCONF = "config.spa_urls"
PLUGINS_URLCONF = "funkwhale_api.common.plugins"
ASGI_APPLICATION = "config.routing.application"

# This ensures that Django will be able to detect a secure connection
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# AUTHENTICATION CONFIGURATION
# ------------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = (
    "funkwhale_api.users.auth_backends.ModelBackend",
    "funkwhale_api.users.auth_backends.AllAuthBackend",
)
SESSION_COOKIE_HTTPONLY = False
# Some really nice defaults
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION_ENFORCE = env.bool(
    "ACCOUNT_EMAIL_VERIFICATION_ENFORCE", default=False
)
"""
Determine wether users need to verify their email address before using the service. Enabling this can be useful
to reduce spam or bots accounts, however, you'll need to configure a mail server so that your users can receive the
verification emails, using :attr:`EMAIL_CONFIG`.

Note that regardless of the setting value, superusers created through the command line will never require verification.

"""
ACCOUNT_EMAIL_VERIFICATION = (
    "mandatory" if ACCOUNT_EMAIL_VERIFICATION_ENFORCE else "optional"
)
ACCOUNT_USERNAME_VALIDATORS = "funkwhale_api.users.serializers.username_validators"

# Custom user app defaults
# Select the correct user model
AUTH_USER_MODEL = "users.User"
LOGIN_REDIRECT_URL = "users:redirect"
LOGIN_URL = "account_login"

# OAuth configuration
from funkwhale_api.users.oauth import scopes  # noqa

OAUTH2_PROVIDER = {
    "SCOPES": {s.id: s.label for s in scopes.SCOPES_BY_ID.values()},
    "ALLOWED_REDIRECT_URI_SCHEMES": ["http", "https", "urn"],
    # we keep expired tokens for 15 days, for tracability
    "REFRESH_TOKEN_EXPIRE_SECONDS": 3600 * 24 * 15,
    "AUTHORIZATION_CODE_EXPIRE_SECONDS": 5 * 60,
    "ACCESS_TOKEN_EXPIRE_SECONDS": 60 * 60 * 10,
    "OAUTH2_SERVER_CLASS": "funkwhale_api.users.oauth.server.OAuth2Server",
}
OAUTH2_PROVIDER_APPLICATION_MODEL = "users.Application"
OAUTH2_PROVIDER_ACCESS_TOKEN_MODEL = "users.AccessToken"
OAUTH2_PROVIDER_GRANT_MODEL = "users.Grant"
OAUTH2_PROVIDER_REFRESH_TOKEN_MODEL = "users.RefreshToken"

SCOPED_TOKENS_MAX_AGE = 60 * 60 * 24 * 3

# LDAP AUTHENTICATION CONFIGURATION
# ------------------------------------------------------------------------------
AUTH_LDAP_ENABLED = env.bool("LDAP_ENABLED", default=False)
"""
Wether to enable LDAP authentication. See :doc:`/installation/ldap` for more information.
"""

if AUTH_LDAP_ENABLED:

    # Import the LDAP modules here; this way, we don't need the dependency unless someone
    # actually enables the LDAP support
    import ldap
    from django_auth_ldap.config import LDAPSearch, LDAPSearchUnion, GroupOfNamesType

    # Add LDAP to the authentication backends
    AUTHENTICATION_BACKENDS += ("django_auth_ldap.backend.LDAPBackend",)

    # Basic configuration
    AUTH_LDAP_SERVER_URI = env("LDAP_SERVER_URI")
    AUTH_LDAP_BIND_DN = env("LDAP_BIND_DN", default="")
    AUTH_LDAP_BIND_PASSWORD = env("LDAP_BIND_PASSWORD", default="")
    AUTH_LDAP_SEARCH_FILTER = env("LDAP_SEARCH_FILTER", default="(uid={0})").format(
        "%(user)s"
    )
    AUTH_LDAP_START_TLS = env.bool("LDAP_START_TLS", default=False)
    AUTH_LDAP_BIND_AS_AUTHENTICATING_USER = env(
        "AUTH_LDAP_BIND_AS_AUTHENTICATING_USER", default=False
    )

    DEFAULT_USER_ATTR_MAP = [
        "first_name:givenName",
        "last_name:sn",
        "username:cn",
        "email:mail",
    ]
    LDAP_USER_ATTR_MAP = env.list("LDAP_USER_ATTR_MAP", default=DEFAULT_USER_ATTR_MAP)
    AUTH_LDAP_USER_ATTR_MAP = {}
    for m in LDAP_USER_ATTR_MAP:
        funkwhale_field, ldap_field = m.split(":")
        AUTH_LDAP_USER_ATTR_MAP[funkwhale_field.strip()] = ldap_field.strip()

    # Determine root DN supporting multiple root DNs
    AUTH_LDAP_ROOT_DN = env("LDAP_ROOT_DN")
    AUTH_LDAP_ROOT_DN_LIST = []
    for ROOT_DN in AUTH_LDAP_ROOT_DN.split():
        AUTH_LDAP_ROOT_DN_LIST.append(
            LDAPSearch(ROOT_DN, ldap.SCOPE_SUBTREE, AUTH_LDAP_SEARCH_FILTER)
        )
    # Search for the user in all the root DNs
    AUTH_LDAP_USER_SEARCH = LDAPSearchUnion(*AUTH_LDAP_ROOT_DN_LIST)

    # Search for group types
    LDAP_GROUP_DN = env("LDAP_GROUP_DN", default="")
    if LDAP_GROUP_DN:
        AUTH_LDAP_GROUP_DN = LDAP_GROUP_DN
        # Get filter
        AUTH_LDAP_GROUP_FILTER = env("LDAP_GROUP_FILER", default="")
        # Search for the group in the specified DN
        AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
            AUTH_LDAP_GROUP_DN, ldap.SCOPE_SUBTREE, AUTH_LDAP_GROUP_FILTER
        )
        AUTH_LDAP_GROUP_TYPE = GroupOfNamesType()

        # Configure basic group support
        LDAP_REQUIRE_GROUP = env("LDAP_REQUIRE_GROUP", default="")
        if LDAP_REQUIRE_GROUP:
            AUTH_LDAP_REQUIRE_GROUP = LDAP_REQUIRE_GROUP
        LDAP_DENY_GROUP = env("LDAP_DENY_GROUP", default="")
        if LDAP_DENY_GROUP:
            AUTH_LDAP_DENY_GROUP = LDAP_DENY_GROUP


# SLUGLIFIER
AUTOSLUG_SLUGIFY_FUNCTION = "slugify.slugify"

CACHE_DEFAULT = "redis://127.0.0.1:6379/0"
CACHE_URL = env.cache_url("CACHE_URL", default=CACHE_DEFAULT)
"""
URL to your redis server. Examples:

- `redis://<host>:<port>/<database>`
- `redis://127.0.0.1:6379/0`
- `redis://:password@localhost:6379/0` for password auth (the extra semicolon is important)
- `redis:///run/redis/redis.sock?db=0` over unix sockets

.. note::

    If you want to use Redis over unix sockets, you'll also need to update :attr:`CELERY_BROKER_URL`

"""
CACHES = {
    "default": CACHE_URL,
    "local": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "local-cache",
    },
}
CACHES["default"]["BACKEND"] = "django_redis.cache.RedisCache"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [CACHES["default"]["LOCATION"]]},
    }
}

CACHES["default"]["OPTIONS"] = {
    "CLIENT_CLASS": "funkwhale_api.common.cache.RedisClient",
    "IGNORE_EXCEPTIONS": True,  # mimics memcache behavior.
    # http://niwinz.github.io/django-redis/latest/#_memcached_exceptions_behavior
}
CACHEOPS_DURATION = env("CACHEOPS_DURATION", default=0)
CACHEOPS_ENABLED = bool(CACHEOPS_DURATION)

if CACHEOPS_ENABLED:
    INSTALLED_APPS += ("cacheops",)
    CACHEOPS_REDIS = env("CACHE_URL", default=CACHE_DEFAULT)
    CACHEOPS_PREFIX = lambda _: "cacheops"  # noqa
    CACHEOPS_DEFAULTS = {"timeout": CACHEOPS_DURATION}
    CACHEOPS = {
        "music.album": {"ops": "count"},
        "music.artist": {"ops": "count"},
        "music.track": {"ops": "count"},
    }

# CELERY
INSTALLED_APPS += ("funkwhale_api.taskapp.celery.CeleryConfig",)
CELERY_BROKER_URL = env(
    "CELERY_BROKER_URL", default=env("CACHE_URL", default=CACHE_DEFAULT)
)
"""
URL to celery's task broker. Defaults to :attr:`CACHE_URL`, so you shouldn't have to tweak this, unless you want
to use a different one, or use Redis sockets to connect.

Exemple:

- `redis://127.0.0.1:6379/0`
- `redis+socket:///run/redis/redis.sock?virtual_host=0`
"""
# END CELERY
# Location of root django.contrib.admin URL, use {% url 'admin:index' %}

# Your common stuff: Below this line define 3rd party library settings
CELERY_TASK_DEFAULT_RATE_LIMIT = 1
CELERY_TASK_TIME_LIMIT = 300
CELERY_BEAT_SCHEDULE = {
    "audio.fetch_rss_feeds": {
        "task": "audio.fetch_rss_feeds",
        "schedule": crontab(minute="0", hour="*"),
        "options": {"expires": 60 * 60},
    },
    "common.prune_unattached_attachments": {
        "task": "common.prune_unattached_attachments",
        "schedule": crontab(minute="0", hour="*"),
        "options": {"expires": 60 * 60},
    },
    "federation.clean_music_cache": {
        "task": "federation.clean_music_cache",
        "schedule": crontab(minute="0", hour="*/2"),
        "options": {"expires": 60 * 2},
    },
    "music.clean_transcoding_cache": {
        "task": "music.clean_transcoding_cache",
        "schedule": crontab(minute="0", hour="*"),
        "options": {"expires": 60 * 2},
    },
    "oauth.clear_expired_tokens": {
        "task": "oauth.clear_expired_tokens",
        "schedule": crontab(minute="0", hour="0"),
        "options": {"expires": 60 * 60 * 24},
    },
    "federation.refresh_nodeinfo_known_nodes": {
        "task": "federation.refresh_nodeinfo_known_nodes",
        "schedule": crontab(
            **env.dict(
                "SCHEDULE_FEDERATION_REFRESH_NODEINFO_KNOWN_NODES",
                default={"minute": "0", "hour": "*"},
            )
        ),
        "options": {"expires": 60 * 60},
    },
}

if env.bool("ADD_ALBUM_TAGS_FROM_TRACKS", default=True):
    CELERY_BEAT_SCHEDULE["music.albums_set_tags_from_tracks"] = {
        "task": "music.albums_set_tags_from_tracks",
        "schedule": crontab(minute="0", hour="4", day_of_week="4"),
        "options": {"expires": 60 * 60 * 2},
    }

if env.bool("ADD_ARTIST_TAGS_FROM_TRACKS", default=True):
    CELERY_BEAT_SCHEDULE["music.artists_set_tags_from_tracks"] = {
        "task": "music.artists_set_tags_from_tracks",
        "schedule": crontab(minute="0", hour="4", day_of_week="4"),
        "options": {"expires": 60 * 60 * 2},
    }

NODEINFO_REFRESH_DELAY = env.int("NODEINFO_REFRESH_DELAY", default=3600 * 24)


def get_user_secret_key(user):
    from django.conf import settings

    return settings.SECRET_KEY + str(user.secret_key)


JWT_AUTH = {
    "JWT_ALLOW_REFRESH": True,
    "JWT_EXPIRATION_DELTA": datetime.timedelta(days=7),
    "JWT_REFRESH_EXPIRATION_DELTA": datetime.timedelta(days=30),
    "JWT_AUTH_HEADER_PREFIX": "JWT",
    "JWT_GET_USER_SECRET_KEY": get_user_secret_key,
}
OLD_PASSWORD_FIELD_ENABLED = True
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": env.int("PASSWORD_MIN_LENGTH", default=8)},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
DISABLE_PASSWORD_VALIDATORS = env.bool("DISABLE_PASSWORD_VALIDATORS", default=False)
"""
Wether to disable password validators (length, common words, similarity with username…) used during regitration.
"""
if DISABLE_PASSWORD_VALIDATORS:
    AUTH_PASSWORD_VALIDATORS = []
ACCOUNT_ADAPTER = "funkwhale_api.users.adapters.FunkwhaleAccountAdapter"
CORS_ORIGIN_ALLOW_ALL = True
# CORS_ORIGIN_WHITELIST = (
#     'localhost',
#     'funkwhale.localhost',
# )
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "funkwhale_api.common.pagination.FunkwhalePagination",
    "PAGE_SIZE": 25,
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
        "funkwhale_api.federation.parsers.ActivityParser",
    ),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "funkwhale_api.common.authentication.OAuth2Authentication",
        "funkwhale_api.common.authentication.JSONWebTokenAuthenticationQS",
        "funkwhale_api.common.authentication.BearerTokenHeaderAuth",
        "funkwhale_api.common.authentication.JSONWebTokenAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "funkwhale_api.users.oauth.permissions.ScopePermission",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "rest_framework.filters.OrderingFilter",
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "NUM_PROXIES": env.int("NUM_PROXIES", default=1),
}
THROTTLING_ENABLED = env.bool("THROTTLING_ENABLED", default=True)
"""
Wether to enable throttling (also known as rate-limiting). Leaving this enabled is recommended
especially on public pods, to improve the quality of service.
"""

if THROTTLING_ENABLED:
    REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = env.list(
        "THROTTLE_CLASSES",
        default=["funkwhale_api.common.throttling.FunkwhaleThrottle"],
    )

THROTTLING_SCOPES = {
    "*": {"anonymous": "anonymous-wildcard", "authenticated": "authenticated-wildcard"},
    "create": {
        "authenticated": "authenticated-create",
        "anonymous": "anonymous-create",
    },
    "list": {"authenticated": "authenticated-list", "anonymous": "anonymous-list"},
    "retrieve": {
        "authenticated": "authenticated-retrieve",
        "anonymous": "anonymous-retrieve",
    },
    "destroy": {
        "authenticated": "authenticated-destroy",
        "anonymous": "anonymous-destroy",
    },
    "update": {
        "authenticated": "authenticated-update",
        "anonymous": "anonymous-update",
    },
    "partial_update": {
        "authenticated": "authenticated-update",
        "anonymous": "anonymous-update",
    },
}

THROTTLING_USER_RATES = env.dict("THROTTLING_RATES", default={})

THROTTLING_RATES = {
    "anonymous-wildcard": {
        "rate": THROTTLING_USER_RATES.get("anonymous-wildcard", "1000/h"),
        "description": "Anonymous requests not covered by other limits",
    },
    "authenticated-wildcard": {
        "rate": THROTTLING_USER_RATES.get("authenticated-wildcard", "2000/h"),
        "description": "Authenticated requests not covered by other limits",
    },
    "authenticated-create": {
        "rate": THROTTLING_USER_RATES.get("authenticated-create", "1000/hour"),
        "description": "Authenticated POST requests",
    },
    "anonymous-create": {
        "rate": THROTTLING_USER_RATES.get("anonymous-create", "1000/day"),
        "description": "Anonymous POST requests",
    },
    "authenticated-list": {
        "rate": THROTTLING_USER_RATES.get("authenticated-list", "10000/hour"),
        "description": "Authenticated GET requests on resource lists",
    },
    "anonymous-list": {
        "rate": THROTTLING_USER_RATES.get("anonymous-list", "10000/day"),
        "description": "Anonymous GET requests on resource lists",
    },
    "authenticated-retrieve": {
        "rate": THROTTLING_USER_RATES.get("authenticated-retrieve", "10000/hour"),
        "description": "Authenticated GET requests on resource detail",
    },
    "anonymous-retrieve": {
        "rate": THROTTLING_USER_RATES.get("anonymous-retrieve", "10000/day"),
        "description": "Anonymous GET requests on resource detail",
    },
    "authenticated-destroy": {
        "rate": THROTTLING_USER_RATES.get("authenticated-destroy", "500/hour"),
        "description": "Authenticated DELETE requests on resource detail",
    },
    "anonymous-destroy": {
        "rate": THROTTLING_USER_RATES.get("anonymous-destroy", "1000/day"),
        "description": "Anonymous DELETE requests on resource detail",
    },
    "authenticated-update": {
        "rate": THROTTLING_USER_RATES.get("authenticated-update", "1000/hour"),
        "description": "Authenticated PATCH and PUT requests on resource detail",
    },
    "anonymous-update": {
        "rate": THROTTLING_USER_RATES.get("anonymous-update", "1000/day"),
        "description": "Anonymous PATCH and PUT requests on resource detail",
    },
    "subsonic": {
        "rate": THROTTLING_USER_RATES.get("subsonic", "2000/hour"),
        "description": "All subsonic API requests",
    },
    # potentially spammy / dangerous endpoints
    "authenticated-reports": {
        "rate": THROTTLING_USER_RATES.get("authenticated-reports", "100/day"),
        "description": "Authenticated report submission",
    },
    "anonymous-reports": {
        "rate": THROTTLING_USER_RATES.get("anonymous-reports", "10/day"),
        "description": "Anonymous report submission",
    },
    "authenticated-oauth-app": {
        "rate": THROTTLING_USER_RATES.get("authenticated-oauth-app", "10/hour"),
        "description": "Authenticated OAuth app creation",
    },
    "anonymous-oauth-app": {
        "rate": THROTTLING_USER_RATES.get("anonymous-oauth-app", "10/day"),
        "description": "Anonymous OAuth app creation",
    },
    "oauth-authorize": {
        "rate": THROTTLING_USER_RATES.get("oauth-authorize", "100/hour"),
        "description": "OAuth app authorization",
    },
    "oauth-token": {
        "rate": THROTTLING_USER_RATES.get("oauth-token", "100/hour"),
        "description": "OAuth token creation",
    },
    "oauth-revoke-token": {
        "rate": THROTTLING_USER_RATES.get("oauth-revoke-token", "100/hour"),
        "description": "OAuth token deletion",
    },
    "login": {
        "rate": THROTTLING_USER_RATES.get("login", "30/hour"),
        "description": "Login",
    },
    "jwt-login": {
        "rate": THROTTLING_USER_RATES.get("jwt-login", "30/hour"),
        "description": "JWT token creation",
    },
    "jwt-refresh": {
        "rate": THROTTLING_USER_RATES.get("jwt-refresh", "30/hour"),
        "description": "JWT token refresh",
    },
    "signup": {
        "rate": THROTTLING_USER_RATES.get("signup", "10/day"),
        "description": "Account creation",
    },
    "verify-email": {
        "rate": THROTTLING_USER_RATES.get("verify-email", "20/h"),
        "description": "Email address confirmation",
    },
    "password-change": {
        "rate": THROTTLING_USER_RATES.get("password-change", "20/h"),
        "description": "Password change (when authenticated)",
    },
    "password-reset": {
        "rate": THROTTLING_USER_RATES.get("password-reset", "20/h"),
        "description": "Password reset request",
    },
    "password-reset-confirm": {
        "rate": THROTTLING_USER_RATES.get("password-reset-confirm", "20/h"),
        "description": "Password reset confirmation",
    },
    "fetch": {
        "rate": THROTTLING_USER_RATES.get("fetch", "200/d"),
        "description": "Fetch remote objects",
    },
}
THROTTLING_RATES = THROTTLING_RATES
"""
Throttling rates for specific endpoints and features of the app. You can tweak this if you are
encountering to severe rate limiting issues or, on the contrary, if you want to reduce
the consumption on some endpoints.

Example:

- ``signup=5/d,password-reset=2/d,anonymous-reports=5/d``
"""

BROWSABLE_API_ENABLED = env.bool("BROWSABLE_API_ENABLED", default=False)
if BROWSABLE_API_ENABLED:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += (
        "rest_framework.renderers.BrowsableAPIRenderer",
    )

REST_AUTH_SERIALIZERS = {
    "PASSWORD_RESET_SERIALIZER": "funkwhale_api.users.serializers.PasswordResetSerializer"  # noqa
}
REST_SESSION_LOGIN = False
REST_USE_JWT = True

ATOMIC_REQUESTS = False
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Wether we should use Apache, Nginx (or other) headers when serving audio files
# Default to Nginx
REVERSE_PROXY_TYPE = env("REVERSE_PROXY_TYPE", default="nginx")
"""
Depending on the reverse proxy used in front of your funkwhale instance,
the API will use different kind of headers to serve audio files

Allowed values: ``nginx``, ``apache2``
"""
assert REVERSE_PROXY_TYPE in ["apache2", "nginx"], "Unsupported REVERSE_PROXY_TYPE"

PROTECT_FILES_PATH = env("PROTECT_FILES_PATH", default="/_protected")
"""
Which path will be used to process the internal redirection to the reverse proxy
**DO NOT** put a slash at the end.

You shouldn't have to tweak this.
"""

MUSICBRAINZ_CACHE_DURATION = env.int("MUSICBRAINZ_CACHE_DURATION", default=300)
"""
How long to cache MusicBrainz results, in seconds
"""
MUSICBRAINZ_HOSTNAME = env("MUSICBRAINZ_HOSTNAME", default="musicbrainz.org")
"""
Use this setting to change the musicbrainz hostname, for instance to
use a mirror. The hostname can also contain a port number.

Example:

- ``mymusicbrainz.mirror``
- ``localhost:5000``

"""
# Custom Admin URL, use {% url 'admin:index' %}
ADMIN_URL = env("DJANGO_ADMIN_URL", default="^api/admin/")
"""
Path to the Django admin area.

Exemples:

- `^api/admin/`
- `^api/mycustompath/`

"""
CSRF_USE_SESSIONS = True
SESSION_ENGINE = "django.contrib.sessions.backends.cache"

# Playlist settings
# XXX: deprecated, see #186
PLAYLISTS_MAX_TRACKS = env.int("PLAYLISTS_MAX_TRACKS", default=250)


ACCOUNT_USERNAME_BLACKLIST = [
    "funkwhale",
    "library",
    "instance",
    "test",
    "status",
    "root",
    "admin",
    "owner",
    "superuser",
    "staff",
    "service",
    "me",
    "ghost",
    "_",
    "-",
    "hello",
    "contact",
    "inbox",
    "outbox",
    "shared-inbox",
    "shared_inbox",
    "actor",
] + env.list("ACCOUNT_USERNAME_BLACKLIST", default=[])
"""
List of usernames that will be unavailable during registration.
"""
EXTERNAL_REQUESTS_VERIFY_SSL = env.bool("EXTERNAL_REQUESTS_VERIFY_SSL", default=True)
"""
Wether to enforce HTTPS certificates verification when doing outgoing HTTP requests (typically with federation).
Disabling this is not recommended.
"""
EXTERNAL_REQUESTS_TIMEOUT = env.int("EXTERNAL_REQUESTS_TIMEOUT", default=10)
"""
Default timeout for external requests.
"""
# XXX: deprecated, see #186
API_AUTHENTICATION_REQUIRED = env.bool("API_AUTHENTICATION_REQUIRED", True)

MUSIC_DIRECTORY_PATH = env("MUSIC_DIRECTORY_PATH", default=None)
"""
The path on your server where Funkwhale can import files using :ref:`in-place import
<in-place-import>`. It must be readable by the webserver and Funkwhale
api and worker processes.

On docker installations, we recommend you use the default of ``/music``
for this value. For non-docker installation, you can use any absolute path.
``/srv/funkwhale/data/music`` is a safe choice if you don't know what to use.

.. note:: This path should not include any trailing slash

.. warning::

   You need to adapt your :ref:`reverse-proxy configuration<reverse-proxy-setup>` to
   serve the directory pointed by ``MUSIC_DIRECTORY_PATH`` on
   ``/_protected/music`` URL.

"""
MUSIC_DIRECTORY_SERVE_PATH = env(
    "MUSIC_DIRECTORY_SERVE_PATH", default=MUSIC_DIRECTORY_PATH
)
"""
Default: :attr:`MUSIC_DIRECTORY_PATH`

When using Docker, the value of :attr:`MUSIC_DIRECTORY_PATH` in your containers
may differ from the real path on your host. Assuming you have the following directive
in your :file:`docker-compose.yml` file::

    volumes:
      - /srv/funkwhale/data/music:/music:ro

Then, the value of :attr:`MUSIC_DIRECTORY_SERVE_PATH` should be
``/srv/funkwhale/data/music``. This must be readable by the webserver.

On non-docker setup, you don't need to configure this setting.

.. note:: This path should not include any trailing slash

"""
# When this is set to default=True, we need to reenable migration music/0042
# to ensure data is populated correctly on existing pods
MUSIC_USE_DENORMALIZATION = env.bool("MUSIC_USE_DENORMALIZATION", default=False)

USERS_INVITATION_EXPIRATION_DAYS = env.int(
    "USERS_INVITATION_EXPIRATION_DAYS", default=14
)
"""
Expiration delay in days, for user invitations.
"""

VERSATILEIMAGEFIELD_RENDITION_KEY_SETS = {
    "square": [
        ("original", "url"),
        ("square_crop", "crop__400x400"),
        ("medium_square_crop", "crop__200x200"),
        ("small_square_crop", "crop__50x50"),
    ],
    "attachment_square": [
        ("original", "url"),
        ("medium_square_crop", "crop__200x200"),
    ],
}
VERSATILEIMAGEFIELD_SETTINGS = {
    "create_images_on_demand": False,
    "jpeg_resize_quality": env.int("THUMBNAIL_JPEG_RESIZE_QUALITY", default=95),
}
RSA_KEY_SIZE = 2048
# for performance gain in tests, since we don't need to actually create the
# thumbnails
CREATE_IMAGE_THUMBNAILS = env.bool("CREATE_IMAGE_THUMBNAILS", default=True)
# we rotate actor keys at most every two days by default
ACTOR_KEY_ROTATION_DELAY = env.int("ACTOR_KEY_ROTATION_DELAY", default=3600 * 48)
SUBSONIC_DEFAULT_TRANSCODING_FORMAT = (
    env("SUBSONIC_DEFAULT_TRANSCODING_FORMAT", default="mp3") or None
)
"""
Default format for transcoding when using Subsonic API.
"""
# extra tags will be ignored
TAGS_MAX_BY_OBJ = env.int("TAGS_MAX_BY_OBJ", default=30)
"""
Maximum number of tags that can be associated with an object. Extra tags will be ignored.
"""
FEDERATION_OBJECT_FETCH_DELAY = env.int(
    "FEDERATION_OBJECT_FETCH_DELAY", default=60 * 24 * 3
)
"""
Number of minutes before a remote object will be automatically refetched when accessed in the UI.
"""
MODERATION_EMAIL_NOTIFICATIONS_ENABLED = env.bool(
    "MODERATION_EMAIL_NOTIFICATIONS_ENABLED", default=True
)
"""
Whether to enable email notifications to moderators and pods admins.
"""
FEDERATION_AUTHENTIFY_FETCHES = True
FEDERATION_SYNCHRONOUS_FETCH = env.bool("FEDERATION_SYNCHRONOUS_FETCH", default=True)
FEDERATION_DUPLICATE_FETCH_DELAY = env.int(
    "FEDERATION_DUPLICATE_FETCH_DELAY", default=60 * 50
)
"""
Delay, in seconds, between two manual fetch of the same remote object.
"""
INSTANCE_SUPPORT_MESSAGE_DELAY = env.int("INSTANCE_SUPPORT_MESSAGE_DELAY", default=15)
"""
Delay in days after signup before we show the "support your pod" message
"""
FUNKWHALE_SUPPORT_MESSAGE_DELAY = env.int("FUNKWHALE_SUPPORT_MESSAGE_DELAY", default=15)
"""
Delay in days after signup before we show the "support Funkwhale" message
"""
# XXX Stable release: remove
USE_FULL_TEXT_SEARCH = env.bool("USE_FULL_TEXT_SEARCH", default=True)

MIN_DELAY_BETWEEN_DOWNLOADS_COUNT = env.int(
    "MIN_DELAY_BETWEEN_DOWNLOADS_COUNT", default=60 * 60 * 6
)
"""
Minimum required period, in seconds, for two downloads of the same track by the same IP
or user to be recorded in statistics.
"""
MARKDOWN_EXTENSIONS = env.list("MARKDOWN_EXTENSIONS", default=["nl2br", "extra"])
"""
List of markdown extensions to enable.

Cf `<https://python-markdown.github.io/extensions/>`_
"""
LINKIFIER_SUPPORTED_TLDS = ["audio"] + env.list("LINKINFIER_SUPPORTED_TLDS", default=[])
"""
Additional TLDs to support with our markdown linkifier.
"""
EXTERNAL_MEDIA_PROXY_ENABLED = env.bool("EXTERNAL_MEDIA_PROXY_ENABLED", default=True)
"""
Wether to proxy attachment files hosted on third party pods and and servers. Keeping
this to true is recommended, to reduce leaking browsing information of your users, and
reduce the bandwidth used on remote pods.
"""
PODCASTS_THIRD_PARTY_VISIBILITY = env("PODCASTS_THIRD_PARTY_VISIBILITY", default="me")
"""
By default, only people who subscribe to a podcast RSS will have access to their episodes.
switch to "instance" or "everyone" to change that.

Changing it only affect new podcasts.
"""
PODCASTS_RSS_FEED_REFRESH_DELAY = env.int(
    "PODCASTS_RSS_FEED_REFRESH_DELAY", default=60 * 60 * 24
)
"""
Delay in seconds between to fetch of RSS feeds. Reducing this mean you'll receive new episodes faster,
but will require more resources.
"""
# maximum items loaded through XML feed
PODCASTS_RSS_FEED_MAX_ITEMS = env.int("PODCASTS_RSS_FEED_MAX_ITEMS", default=250)
"""
Maximum number of RSS items to load in each podcast feed.
"""

IGNORE_FORWARDED_HOST_AND_PROTO = env.bool(
    "IGNORE_FORWARDED_HOST_AND_PROTO", default=True
)
"""
Use :attr:`FUNKWHALE_HOSTNAME` and :attr:`FUNKWHALE_PROTOCOL ` instead of request header.
"""

HASHING_ALGORITHM = "sha256"
HASHING_CHUNK_SIZE = 1024 * 100

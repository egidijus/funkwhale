# -*- coding: utf-8 -*-
"""
Django settings for funkwhale_api project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""
from __future__ import absolute_import, unicode_literals

import datetime
import logging.config
import sys

from urllib.parse import urlsplit

import environ
from celery.schedules import crontab

from funkwhale_api import __version__

logger = logging.getLogger("funkwhale_api.config")
ROOT_DIR = environ.Path(__file__) - 3  # (/a/b/myfile.py - 3 = /)
APPS_DIR = ROOT_DIR.path("funkwhale_api")

env = environ.Env()

LOGLEVEL = env("LOGLEVEL", default="info").upper()
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

env_file = env("ENV_FILE", default=None)
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

FUNKWHALE_PLUGINS_PATH = env.list(
    "FUNKWHALE_PLUGINS_PATH",
    default=["/srv/funkwhale/plugins/", str(ROOT_DIR.path("plugins"))],
)

for path in FUNKWHALE_PLUGINS_PATH:
    sys.path.append(path)

print("HELLO", sys.path)
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
        FUNKWHALE_PROTOCOL = env("FUNKWHALE_PROTOCOL", default="https")
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
FUNKWHALE_SPA_HTML_CACHE_DURATION = env.int(
    "FUNKWHALE_SPA_HTML_CACHE_DURATION", default=60 * 15
)
FUNKWHALE_EMBED_URL = env(
    "FUNKWHALE_EMBED_URL", default=FUNKWHALE_URL + "/front/embed.html"
)
APP_NAME = "Funkwhale"

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
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[]) + [FUNKWHALE_HOSTNAME]

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
    "funkwhale_api.plugins",
    "funkwhale_api.activity.apps.ActivityConfig",
    "funkwhale_api.users",  # custom users app
    "funkwhale_api.users.oauth",
    # Your stuff: custom apps go here
    "funkwhale_api.instance",
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


PLUGINS = [p for p in env.list("FUNKWHALE_PLUGINS", default=[]) if p]
if PLUGINS:
    logger.info("Running with the following plugins enabled: %s", ", ".join(PLUGINS))
else:
    logger.info("Running with no plugins")

INSTALLED_APPS = (
    DJANGO_APPS
    + THIRD_PARTY_APPS
    + LOCAL_APPS
    + tuple(["{}.apps.Plugin".format(p) for p in PLUGINS])
)

# MIDDLEWARE CONFIGURATION
# ------------------------------------------------------------------------------
MIDDLEWARE = (
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "funkwhale_api.common.middleware.SPAFallbackMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "funkwhale_api.users.middleware.RecordActivityMiddleware",
    "funkwhale_api.common.middleware.ThrottleStatusMiddleware",
)

# DEBUG
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)

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

EMAIL_SUBJECT_PREFIX = env("EMAIL_SUBJECT_PREFIX", default="[Funkwhale] ")
SERVER_EMAIL = env("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)


EMAIL_CONFIG = env.email_url("EMAIL_CONFIG", default="consolemail://")

vars().update(EMAIL_CONFIG)

# DATABASE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    # Raises ImproperlyConfigured exception if DATABASE_URL not in os.environ
    "default": env.db("DATABASE_URL")
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DATABASES["default"]["CONN_MAX_AGE"] = env("DB_CONN_MAX_AGE", default=60 * 5)

MIGRATION_MODULES = {
    # see https://github.com/jazzband/django-oauth-toolkit/issues/634
    # swappable models are badly designed in oauth2_provider
    # ignore migrations and provide our own models.
    "oauth2_provider": None,
    "sites": "funkwhale_api.contrib.sites.migrations",
}

#
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': 'db.sqlite3',
#     }
# }
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

# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = env("STATIC_URL", default="/staticfiles/")
DEFAULT_FILE_STORAGE = "funkwhale_api.common.storage.ASCIIFileSystemStorage"

PROXY_MEDIA = env.bool("PROXY_MEDIA", default=True)
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = env.bool("AWS_QUERYSTRING_AUTH", default=not PROXY_MEDIA)
AWS_S3_MAX_MEMORY_SIZE = env.int(
    "AWS_S3_MAX_MEMORY_SIZE", default=1000 * 1000 * 1000 * 20
)
AWS_QUERYSTRING_EXPIRE = env.int("AWS_QUERYSTRING_EXPIRE", default=3600)
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default=None)

if AWS_ACCESS_KEY_ID:
    AWS_ACCESS_KEY_ID = AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default=None)
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_LOCATION = env("AWS_LOCATION", default="")
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

# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = env("MEDIA_URL", default="/media/")
FILE_UPLOAD_PERMISSIONS = 0o644
# URL Configuration
# ------------------------------------------------------------------------------
ROOT_URLCONF = "config.urls"
SPA_URLCONF = "config.spa_urls"
ASGI_APPLICATION = "config.routing.application"

# This ensures that Django will be able to detect a secure connection
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# AUTHENTICATION CONFIGURATION
# ------------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = (
    "funkwhale_api.users.auth_backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)
SESSION_COOKIE_HTTPONLY = False
# Some really nice defaults
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
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

# LDAP AUTHENTICATION CONFIGURATION
# ------------------------------------------------------------------------------
AUTH_LDAP_ENABLED = env.bool("LDAP_ENABLED", default=False)
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
CACHES = {
    "default": env.cache_url("CACHE_URL", default=CACHE_DEFAULT),
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
    "CLIENT_CLASS": "django_redis.client.DefaultClient",
    "IGNORE_EXCEPTIONS": True,  # mimics memcache behavior.
    # http://niwinz.github.io/django-redis/latest/#_memcached_exceptions_behavior
}


# CELERY
INSTALLED_APPS += ("funkwhale_api.taskapp.celery.CeleryConfig",)
CELERY_BROKER_URL = env(
    "CELERY_BROKER_URL", default=env("CACHE_URL", default=CACHE_DEFAULT)
)
# END CELERY
# Location of root django.contrib.admin URL, use {% url 'admin:index' %}

# Your common stuff: Below this line define 3rd party library settings
CELERY_TASK_DEFAULT_RATE_LIMIT = 1
CELERY_TASK_TIME_LIMIT = 300
CELERY_BEAT_SCHEDULE = {
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
        "schedule": crontab(minute="0", hour="*"),
        "options": {"expires": 60 * 60},
    },
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
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
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
}


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
assert REVERSE_PROXY_TYPE in ["apache2", "nginx"], "Unsupported REVERSE_PROXY_TYPE"

# Which path will be used to process the internal redirection
# **DO NOT** put a slash at the end
PROTECT_FILES_PATH = env("PROTECT_FILES_PATH", default="/_protected")


# use this setting to tweak for how long you want to cache
# musicbrainz results. (value is in seconds)
MUSICBRAINZ_CACHE_DURATION = env.int("MUSICBRAINZ_CACHE_DURATION", default=300)

# Use this setting to change the musicbrainz hostname, for instance to
# use a mirror. The hostname can also contain a port number (so, e.g.,
# "localhost:5000" is a valid name to set).
MUSICBRAINZ_HOSTNAME = env("MUSICBRAINZ_HOSTNAME", default="musicbrainz.org")

# Custom Admin URL, use {% url 'admin:index' %}
ADMIN_URL = env("DJANGO_ADMIN_URL", default="^api/admin/")
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

EXTERNAL_REQUESTS_VERIFY_SSL = env.bool("EXTERNAL_REQUESTS_VERIFY_SSL", default=True)
# XXX: deprecated, see #186
API_AUTHENTICATION_REQUIRED = env.bool("API_AUTHENTICATION_REQUIRED", True)

MUSIC_DIRECTORY_PATH = env("MUSIC_DIRECTORY_PATH", default=None)
# on Docker setup, the music directory may not match the host path,
# and we need to know it for it to serve stuff properly
MUSIC_DIRECTORY_SERVE_PATH = env(
    "MUSIC_DIRECTORY_SERVE_PATH", default=MUSIC_DIRECTORY_PATH
)

USERS_INVITATION_EXPIRATION_DAYS = env.int(
    "USERS_INVITATION_EXPIRATION_DAYS", default=14
)

VERSATILEIMAGEFIELD_RENDITION_KEY_SETS = {
    "square": [
        ("original", "url"),
        ("square_crop", "crop__400x400"),
        ("medium_square_crop", "crop__200x200"),
        ("small_square_crop", "crop__50x50"),
    ]
}
VERSATILEIMAGEFIELD_SETTINGS = {"create_images_on_demand": False}
RSA_KEY_SIZE = 2048
# for performance gain in tests, since we don't need to actually create the
# thumbnails
CREATE_IMAGE_THUMBNAILS = env.bool("CREATE_IMAGE_THUMBNAILS", default=True)
# we rotate actor keys at most every two days by default
ACTOR_KEY_ROTATION_DELAY = env.int("ACTOR_KEY_ROTATION_DELAY", default=3600 * 48)
SUBSONIC_DEFAULT_TRANSCODING_FORMAT = (
    env("SUBSONIC_DEFAULT_TRANSCODING_FORMAT", default="mp3") or None
)

# extra tags will be ignored
TAGS_MAX_BY_OBJ = env.int("TAGS_MAX_BY_OBJ", default=30)
FEDERATION_OBJECT_FETCH_DELAY = env.int(
    "FEDERATION_OBJECT_FETCH_DELAY", default=60 * 24 * 3
)

MODERATION_EMAIL_NOTIFICATIONS_ENABLED = env.bool(
    "MODERATION_EMAIL_NOTIFICATIONS_ENABLED", default=True
)

# Delay in days after signup before we show the "support us" messages
INSTANCE_SUPPORT_MESSAGE_DELAY = env.int("INSTANCE_SUPPORT_MESSAGE_DELAY", default=15)
FUNKWHALE_SUPPORT_MESSAGE_DELAY = env.int("FUNKWHALE_SUPPORT_MESSAGE_DELAY", default=15)

import cryptography
import logging
import datetime
import urllib.parse
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from rest_framework import authentication, exceptions as rest_exceptions
from funkwhale_api.common import preferences
from funkwhale_api.moderation import models as moderation_models
from . import actors, exceptions, keys, models, signing, tasks, utils


logger = logging.getLogger(__name__)


class SignatureAuthentication(authentication.BaseAuthentication):
    def authenticate_actor(self, request):
        headers = utils.clean_wsgi_headers(request.META)
        try:
            signature = headers["Signature"]
            key_id = keys.get_key_id_from_signature_header(signature)
        except KeyError:
            return
        except ValueError as e:
            raise rest_exceptions.AuthenticationFailed(str(e))

        try:
            actor_url = key_id.split("#")[0]
        except (TypeError, IndexError, AttributeError):
            raise rest_exceptions.AuthenticationFailed("Invalid key id")

        policies = (
            moderation_models.InstancePolicy.objects.active()
            .filter(block_all=True)
            .matching_url(actor_url)
        )
        if policies.exists():
            raise exceptions.BlockedActorOrDomain()

        if request.method.lower() == "get" and preferences.get(
            "moderation__allow_list_enabled"
        ):
            # Only GET requests because POST requests with messages will be handled through
            # MRF
            domain = urllib.parse.urlparse(actor_url).hostname
            allowed = models.Domain.objects.filter(name=domain, allowed=True).exists()
            if not allowed:
                logger.debug("Actor domain %s is not on allow-list", domain)
                raise exceptions.BlockedActorOrDomain()

        try:
            actor = actors.get_actor(actor_url)
        except Exception as e:
            logger.info(
                "Discarding HTTP request from actor/domain %s, %s", actor_url, str(e),
            )
            raise rest_exceptions.AuthenticationFailed(
                "Cannot fetch remote actor to authenticate signature"
            )

        if not actor.public_key:
            raise rest_exceptions.AuthenticationFailed("No public key found")

        try:
            signing.verify_django(request, actor.public_key.encode("utf-8"))
        except cryptography.exceptions.InvalidSignature:
            # in case of invalid signature, we refetch the actor object
            # to load a potentially new public key. This process is called
            # Blind key rotation, and is described at
            # https://blog.dereferenced.org/the-case-for-blind-key-rotation
            # if signature verification fails after that, then we return a 403 error
            actor = actors.get_actor(actor_url, skip_cache=True)
            signing.verify_django(request, actor.public_key.encode("utf-8"))

        # we trigger a nodeinfo update on the actor's domain, if needed
        fetch_delay = 24 * 3600
        now = timezone.now()
        last_fetch = actor.domain.nodeinfo_fetch_date
        if not last_fetch or (
            last_fetch < (now - datetime.timedelta(seconds=fetch_delay))
        ):
            tasks.update_domain_nodeinfo(domain_name=actor.domain.name)
            actor.domain.refresh_from_db()
        return actor

    def authenticate(self, request):
        setattr(request, "actor", None)
        actor = self.authenticate_actor(request)
        if not actor:
            return
        user = AnonymousUser()
        setattr(request, "actor", actor)
        return (user, None)

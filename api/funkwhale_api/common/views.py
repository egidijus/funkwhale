import logging
import time

from django.conf import settings
from django.db import transaction

from rest_framework.decorators import action
from rest_framework import exceptions
from rest_framework import mixins
from rest_framework import permissions
from rest_framework import response
from rest_framework import views
from rest_framework import viewsets

from config import plugins

from funkwhale_api.users.oauth import permissions as oauth_permissions

from . import filters
from . import models
from . import mutations
from . import serializers
from . import signals
from . import tasks
from . import throttling
from . import utils


logger = logging.getLogger(__name__)


class SkipFilterForGetObject:
    def get_object(self, *args, **kwargs):
        setattr(self.request, "_skip_filters", True)
        return super().get_object(*args, **kwargs)

    def filter_queryset(self, queryset):
        if getattr(self.request, "_skip_filters", False):
            return queryset
        return super().filter_queryset(queryset)


class MutationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "uuid"
    queryset = (
        models.Mutation.objects.all()
        .exclude(target_id=None)
        .order_by("-creation_date")
        .select_related("created_by", "approved_by")
        .prefetch_related("target")
    )
    serializer_class = serializers.APIMutationSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ("creation_date",)
    filterset_class = filters.MutationFilter

    def perform_destroy(self, instance):
        if instance.is_applied:
            raise exceptions.PermissionDenied("You cannot delete an applied mutation")

        actor = self.request.user.actor
        is_owner = actor == instance.created_by

        if not any(
            [
                is_owner,
                mutations.registry.has_perm(
                    perm="approve", type=instance.type, obj=instance.target, actor=actor
                ),
            ]
        ):
            raise exceptions.PermissionDenied()

        return super().perform_destroy(instance)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def approve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_applied:
            return response.Response(
                {"error": "This mutation was already applied"}, status=403
            )
        actor = self.request.user.actor
        can_approve = mutations.registry.has_perm(
            perm="approve", type=instance.type, obj=instance.target, actor=actor
        )

        if not can_approve:
            raise exceptions.PermissionDenied()
        previous_is_approved = instance.is_approved
        instance.approved_by = actor
        instance.is_approved = True
        instance.save(update_fields=["approved_by", "is_approved"])
        utils.on_commit(tasks.apply_mutation.delay, mutation_id=instance.id)
        utils.on_commit(
            signals.mutation_updated.send,
            sender=None,
            mutation=instance,
            old_is_approved=previous_is_approved,
            new_is_approved=instance.is_approved,
        )
        return response.Response({}, status=200)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reject(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_applied:
            return response.Response(
                {"error": "This mutation was already applied"}, status=403
            )
        actor = self.request.user.actor
        can_approve = mutations.registry.has_perm(
            perm="approve", type=instance.type, obj=instance.target, actor=actor
        )

        if not can_approve:
            raise exceptions.PermissionDenied()
        previous_is_approved = instance.is_approved
        instance.approved_by = actor
        instance.is_approved = False
        instance.save(update_fields=["approved_by", "is_approved"])
        utils.on_commit(
            signals.mutation_updated.send,
            sender=None,
            mutation=instance,
            old_is_approved=previous_is_approved,
            new_is_approved=instance.is_approved,
        )
        return response.Response({}, status=200)


class RateLimitView(views.APIView):
    permission_classes = []
    throttle_classes = []

    def get(self, request, *args, **kwargs):
        ident = throttling.get_ident(getattr(request, "user", None), request)
        data = {
            "enabled": settings.THROTTLING_ENABLED,
            "ident": ident,
            "scopes": throttling.get_status(ident, time.time()),
        }
        return response.Response(data, status=200)


class AttachmentViewSet(
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "uuid"
    queryset = models.Attachment.objects.all()
    serializer_class = serializers.AttachmentSerializer
    permission_classes = [oauth_permissions.ScopePermission]
    required_scope = "libraries"
    anonymous_policy = "setting"

    @action(
        detail=True, methods=["get"], permission_classes=[], authentication_classes=[]
    )
    @transaction.atomic
    def proxy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not settings.EXTERNAL_MEDIA_PROXY_ENABLED:
            r = response.Response(status=302)
            r["Location"] = instance.url
            return r

        size = request.GET.get("next", "original").lower()
        if size not in ["original", "medium_square_crop", "large_square_crop"]:
            size = "original"

        try:
            tasks.fetch_remote_attachment(instance)
        except Exception:
            logger.exception("Error while fetching attachment %s", instance.url)
            return response.Response(status=500)
        data = self.serializer_class(instance).data
        redirect = response.Response(status=302)
        redirect["Location"] = data["urls"][size]
        return redirect

    def perform_create(self, serializer):
        return serializer.save(actor=self.request.user.actor)

    def perform_destroy(self, instance):
        if instance.actor is None or instance.actor != self.request.user.actor:
            raise exceptions.PermissionDenied()
        instance.delete()


class TextPreviewView(views.APIView):
    permission_classes = []

    def post(self, request, *args, **kwargs):
        payload = request.data
        if "text" not in payload:
            return response.Response({"detail": "Invalid input"}, status=400)

        permissive = payload.get("permissive", False)
        data = {
            "rendered": utils.render_html(
                payload["text"], "text/markdown", permissive=permissive
            )
        }
        return response.Response(data, status=200)


class PluginViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    required_scope = "plugins"
    serializer_class = serializers.serializers.Serializer
    queryset = models.PluginConfiguration.objects.none()

    def list(self, request, *args, **kwargs):
        user = request.user
        user_plugins = [p for p in plugins._plugins.values() if p["user"] is True]

        return response.Response(
            [
                plugins.serialize_plugin(p, confs=plugins.get_confs(user=user))
                for p in user_plugins
            ]
        )

    def retrieve(self, request, *args, **kwargs):
        user = request.user
        user_plugin = [
            p
            for p in plugins._plugins.values()
            if p["user"] is True and p["name"] == kwargs["pk"]
        ]
        if not user_plugin:
            return response.Response(status=404)

        return response.Response(
            plugins.serialize_plugin(user_plugin[0], confs=plugins.get_confs(user=user))
        )

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        user = request.user
        confs = plugins.get_confs(user=user)

        user_plugin = [
            p
            for p in plugins._plugins.values()
            if p["user"] is True and p["name"] == kwargs["pk"]
        ]
        if kwargs["pk"] not in confs:
            return response.Response(status=404)
        plugins.set_conf(kwargs["pk"], request.data, user)
        return response.Response(
            plugins.serialize_plugin(user_plugin[0], confs=plugins.get_confs(user=user))
        )

    def delete(self, request, *args, **kwargs):
        user = request.user
        confs = plugins.get_confs(user=user)
        if kwargs["pk"] not in confs:
            return response.Response(status=404)

        user.plugins.filter(code=kwargs["pk"]).delete()
        return response.Response(status=204)

    @action(detail=True, methods=["post"])
    def enable(self, request, *args, **kwargs):
        user = request.user
        if kwargs["pk"] not in plugins._plugins:
            return response.Response(status=404)
        plugins.enable_conf(kwargs["pk"], True, user)
        return response.Response({}, status=200)

    @action(detail=True, methods=["post"])
    def disable(self, request, *args, **kwargs):
        user = request.user
        if kwargs["pk"] not in plugins._plugins:
            return response.Response(status=404)
        plugins.enable_conf(kwargs["pk"], False, user)
        return response.Response({}, status=200)

    @action(detail=True, methods=["post"])
    def scan(self, request, *args, **kwargs):
        user = request.user
        if kwargs["pk"] not in plugins._plugins:
            return response.Response(status=404)
        conf = plugins.get_conf(kwargs["pk"], user=user)

        if not conf["enabled"]:
            return response.Response(status=405)

        library = request.user.actor.libraries.get(uuid=conf["conf"]["library"])
        hook = [
            hook
            for p, hook in plugins._hooks.get(plugins.SCAN, [])
            if p == kwargs["pk"]
        ]

        if not hook:
            return response.Response(status=405)

        hook[0](library=library, conf=conf["conf"])

        return response.Response({}, status=200)

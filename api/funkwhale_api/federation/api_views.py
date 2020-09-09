import requests.exceptions

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q

from rest_framework import decorators
from rest_framework import mixins
from rest_framework import permissions
from rest_framework import response
from rest_framework import viewsets

from funkwhale_api.common import preferences
from funkwhale_api.common import utils as common_utils
from funkwhale_api.common.permissions import ConditionalAuthentication
from funkwhale_api.music import models as music_models
from funkwhale_api.music import views as music_views
from funkwhale_api.users.oauth import permissions as oauth_permissions

from . import activity
from . import api_serializers
from . import exceptions
from . import filters
from . import models
from . import routes
from . import serializers
from . import tasks
from . import utils


@transaction.atomic
def update_follow(follow, approved):
    follow.approved = approved
    follow.save(update_fields=["approved"])
    if approved:
        routes.outbox.dispatch({"type": "Accept"}, context={"follow": follow})
    else:
        routes.outbox.dispatch({"type": "Reject"}, context={"follow": follow})


class LibraryFollowViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "uuid"
    queryset = (
        models.LibraryFollow.objects.all()
        .order_by("-creation_date")
        .select_related("actor", "target__actor")
    )
    serializer_class = api_serializers.LibraryFollowSerializer
    permission_classes = [oauth_permissions.ScopePermission]
    required_scope = "follows"
    filterset_class = filters.LibraryFollowFilter
    ordering_fields = ("creation_date",)

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(actor=self.request.user.actor).exclude(approved=False)

    def perform_create(self, serializer):
        follow = serializer.save(actor=self.request.user.actor)
        routes.outbox.dispatch({"type": "Follow"}, context={"follow": follow})

    @transaction.atomic
    def perform_destroy(self, instance):
        routes.outbox.dispatch(
            {"type": "Undo", "object": {"type": "Follow"}}, context={"follow": instance}
        )
        instance.delete()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["actor"] = self.request.user.actor
        return context

    @decorators.action(methods=["post"], detail=True)
    def accept(self, request, *args, **kwargs):
        try:
            follow = self.queryset.get(
                target__actor=self.request.user.actor, uuid=kwargs["uuid"]
            )
        except models.LibraryFollow.DoesNotExist:
            return response.Response({}, status=404)
        update_follow(follow, approved=True)
        return response.Response(status=204)

    @decorators.action(methods=["post"], detail=True)
    def reject(self, request, *args, **kwargs):
        try:
            follow = self.queryset.get(
                target__actor=self.request.user.actor, uuid=kwargs["uuid"]
            )
        except models.LibraryFollow.DoesNotExist:
            return response.Response({}, status=404)

        update_follow(follow, approved=False)
        return response.Response(status=204)

    @decorators.action(methods=["get"], detail=False)
    def all(self, request, *args, **kwargs):
        """
        Return all the subscriptions of the current user, with only limited data
        to have a performant endpoint and avoid lots of queries just to display
        subscription status in the UI
        """
        follows = list(
            self.get_queryset().values_list("uuid", "target__uuid", "approved")
        )

        payload = {
            "results": [
                {"uuid": str(u[0]), "library": str(u[1]), "approved": u[2]}
                for u in follows
            ],
            "count": len(follows),
        }
        return response.Response(payload, status=200)


class LibraryViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    lookup_field = "uuid"
    queryset = (
        music_models.Library.objects.all()
        .order_by("-creation_date")
        .select_related("actor__user")
        .annotate(_uploads_count=Count("uploads"))
    )
    serializer_class = api_serializers.LibrarySerializer
    permission_classes = [oauth_permissions.ScopePermission]
    required_scope = "libraries"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.viewable_by(actor=self.request.user.actor)

    @decorators.action(methods=["post"], detail=True)
    def scan(self, request, *args, **kwargs):
        library = self.get_object()
        if library.actor.get_user():
            return response.Response({"status": "skipped"}, 200)

        scan = library.schedule_scan(actor=request.user.actor)
        if scan:
            return response.Response(
                {
                    "status": "scheduled",
                    "scan": api_serializers.LibraryScanSerializer(scan).data,
                },
                200,
            )
        return response.Response({"status": "skipped"}, 200)

    @decorators.action(methods=["post"], detail=False)
    def fetch(self, request, *args, **kwargs):
        try:
            fid = request.data["fid"]
        except KeyError:
            return response.Response({"fid": ["This field is required"]})
        try:
            library = utils.retrieve_ap_object(
                fid,
                actor=request.user.actor,
                queryset=self.queryset,
                serializer_class=serializers.LibrarySerializer,
            )
        except exceptions.BlockedActorOrDomain:
            return response.Response(
                {"detail": "This domain/account is blocked on your instance."},
                status=400,
            )
        except requests.exceptions.RequestException as e:
            return response.Response(
                {"detail": "Error while fetching the library: {}".format(str(e))},
                status=400,
            )
        except serializers.serializers.ValidationError as e:
            return response.Response(
                {"detail": "Invalid data in remote library: {}".format(str(e))},
                status=400,
            )
        serializer = self.serializer_class(library)
        return response.Response({"count": 1, "results": [serializer.data]})


class InboxItemViewSet(
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):

    queryset = (
        models.InboxItem.objects.select_related("activity__actor")
        .prefetch_related("activity__object", "activity__target")
        .filter(activity__type__in=activity.BROADCAST_TO_USER_ACTIVITIES, type="to")
        .order_by("-activity__creation_date")
    )
    serializer_class = api_serializers.InboxItemSerializer
    permission_classes = [oauth_permissions.ScopePermission]
    required_scope = "notifications"
    filterset_class = filters.InboxItemFilter
    ordering_fields = ("activity__creation_date",)

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(actor=self.request.user.actor)

    @decorators.action(methods=["post"], detail=False)
    def action(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = api_serializers.InboxItemActionSerializer(
            request.data, queryset=queryset
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return response.Response(result, status=200)


class FetchViewSet(
    mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):

    queryset = models.Fetch.objects.select_related("actor")
    serializer_class = api_serializers.FetchSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttling_scopes = {"create": {"authenticated": "fetch"}}

    def get_queryset(self):
        return super().get_queryset().filter(actor=self.request.user.actor)

    def perform_create(self, serializer):
        fetch = serializer.save(actor=self.request.user.actor)
        if fetch.status == "finished":
            # a duplicate was returned, no need to fetch again
            return
        if settings.FEDERATION_SYNCHRONOUS_FETCH:
            tasks.fetch(fetch_id=fetch.pk)
            fetch.refresh_from_db()
        else:
            common_utils.on_commit(tasks.fetch.delay, fetch_id=fetch.pk)


class DomainViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    queryset = models.Domain.objects.order_by("name").external()
    permission_classes = [ConditionalAuthentication]
    serializer_class = api_serializers.DomainSerializer
    ordering_fields = ("creation_date", "name")
    max_page_size = 100

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.exclude(
            instance_policy__is_active=True, instance_policy__block_all=True
        )
        if preferences.get("moderation__allow_list_enabled"):
            qs = qs.filter(allowed=True)
        return qs


class ActorViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = models.Actor.objects.select_related(
        "user", "channel", "summary_obj", "attachment_icon"
    )
    permission_classes = [ConditionalAuthentication]
    serializer_class = api_serializers.FullActorSerializer
    lookup_field = "full_username"
    lookup_value_regex = r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)"

    def get_object(self):
        queryset = self.get_queryset()
        username, domain = self.kwargs["full_username"].split("@", 1)
        return queryset.get(preferred_username=username, domain_id=domain)

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.exclude(
            domain__instance_policy__is_active=True,
            domain__instance_policy__block_all=True,
        )
        if preferences.get("moderation__allow_list_enabled"):
            query = Q(domain_id=settings.FUNKWHALE_HOSTNAME) | Q(domain__allowed=True)
            qs = qs.filter(query)
        return qs

    libraries = decorators.action(methods=["get"], detail=True)(
        music_views.get_libraries(
            filter_uploads=lambda o, uploads: uploads.filter(library__actor=o)
        )
    )

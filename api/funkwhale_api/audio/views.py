from rest_framework import decorators
from rest_framework import exceptions
from rest_framework import mixins
from rest_framework import permissions as rest_permissions
from rest_framework import response
from rest_framework import viewsets

from django import http
from django.db import transaction
from django.db.models import Count, Prefetch, Q, Sum
from django.utils import timezone

from funkwhale_api.common import locales
from funkwhale_api.common import permissions
from funkwhale_api.common import preferences
from funkwhale_api.common import utils as common_utils
from funkwhale_api.common.mixins import MultipleLookupDetailMixin
from funkwhale_api.federation import actors
from funkwhale_api.federation import models as federation_models
from funkwhale_api.federation import routes
from funkwhale_api.federation import tasks as federation_tasks
from funkwhale_api.federation import utils as federation_utils
from funkwhale_api.music import models as music_models
from funkwhale_api.music import views as music_views
from funkwhale_api.users.oauth import permissions as oauth_permissions

from . import categories, filters, models, renderers, serializers

ARTIST_PREFETCH_QS = (
    music_models.Artist.objects.select_related("description", "attachment_cover",)
    .prefetch_related(music_views.TAG_PREFETCH)
    .annotate(_tracks_count=Count("tracks"))
)


class ChannelsMixin(object):
    def dispatch(self, request, *args, **kwargs):
        if not preferences.get("audio__channels_enabled"):
            return http.HttpResponse(status=405)
        return super().dispatch(request, *args, **kwargs)


class ChannelViewSet(
    ChannelsMixin,
    MultipleLookupDetailMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    url_lookups = [
        {
            "lookup_field": "uuid",
            "validator": serializers.serializers.UUIDField().to_internal_value,
        },
        {
            "lookup_field": "username",
            "validator": federation_utils.get_actor_data_from_username,
            "get_query": lambda v: Q(
                actor__domain=v["domain"],
                actor__preferred_username__iexact=v["username"],
            ),
        },
    ]
    filterset_class = filters.ChannelFilter
    serializer_class = serializers.ChannelSerializer
    queryset = (
        models.Channel.objects.all()
        .prefetch_related(
            "library",
            "attributed_to",
            "actor",
            Prefetch("artist", queryset=ARTIST_PREFETCH_QS),
        )
        .order_by("-creation_date")
    )
    permission_classes = [
        oauth_permissions.ScopePermission,
        permissions.OwnerPermission,
    ]
    required_scope = "libraries"
    anonymous_policy = "setting"
    owner_checks = ["write"]
    owner_field = "attributed_to.user"
    owner_exception = exceptions.PermissionDenied

    def get_serializer_class(self):
        if self.request.method.lower() in ["head", "get", "options"]:
            return serializers.ChannelSerializer
        elif self.action in ["update", "partial_update"]:
            return serializers.ChannelUpdateSerializer
        return serializers.ChannelCreateSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "retrieve":
            queryset = queryset.annotate(
                _downloads_count=Sum("artist__tracks__downloads_count")
            )
        return queryset

    def perform_create(self, serializer):
        return serializer.save(attributed_to=self.request.user.actor)

    def list(self, request, *args, **kwargs):
        if self.request.GET.get("output") == "opml":
            queryset = self.filter_queryset(self.get_queryset())[:500]
            opml = serializers.get_opml(
                channels=queryset,
                date=timezone.now(),
                title="Funkwhale channels OPML export",
            )
            xml_body = renderers.render_xml(renderers.dict_to_xml_tree("opml", opml))
            return http.HttpResponse(xml_body, content_type="application/xml")

        else:
            return super().list(request, *args, **kwargs)

    def get_object(self):
        obj = super().get_object()
        if (
            self.action == "retrieve"
            and self.request.GET.get("refresh", "").lower() == "true"
        ):
            obj = music_views.refetch_obj(obj, self.get_queryset())
        return obj

    @decorators.action(
        detail=True,
        methods=["post"],
        permission_classes=[rest_permissions.IsAuthenticated],
    )
    def subscribe(self, request, *args, **kwargs):
        object = self.get_object()
        subscription = federation_models.Follow(actor=request.user.actor)
        subscription.fid = subscription.get_federation_id()
        subscription, created = SubscriptionsViewSet.queryset.get_or_create(
            target=object.actor,
            actor=request.user.actor,
            defaults={
                "approved": True,
                "fid": subscription.fid,
                "uuid": subscription.uuid,
            },
        )
        # prefetch stuff
        subscription = SubscriptionsViewSet.queryset.get(pk=subscription.pk)
        if not object.actor.is_local:
            routes.outbox.dispatch({"type": "Follow"}, context={"follow": subscription})

        data = serializers.SubscriptionSerializer(subscription).data
        return response.Response(data, status=201)

    @decorators.action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[rest_permissions.IsAuthenticated],
    )
    def unsubscribe(self, request, *args, **kwargs):
        object = self.get_object()
        follow_qs = request.user.actor.emitted_follows.filter(target=object.actor)
        follow = follow_qs.first()
        if follow:
            if not object.actor.is_local:
                routes.outbox.dispatch(
                    {"type": "Undo", "object": {"type": "Follow"}},
                    context={"follow": follow},
                )
            follow_qs.delete()
        return response.Response(status=204)

    @decorators.action(
        detail=True,
        methods=["get"],
        content_negotiation_class=renderers.PodcastRSSContentNegociation,
    )
    def rss(self, request, *args, **kwargs):
        object = self.get_object()
        if not object.attributed_to.is_local:
            return response.Response({"detail": "Not found"}, status=404)

        if object.attributed_to == actors.get_service_actor():
            # external feed, we redirect to the canonical one
            return http.HttpResponseRedirect(object.rss_url)

        uploads = (
            object.library.uploads.playable_by(None)
            .prefetch_related(
                Prefetch(
                    "track",
                    queryset=music_models.Track.objects.select_related(
                        "attachment_cover", "description"
                    ).prefetch_related(music_views.TAG_PREFETCH,),
                ),
            )
            .select_related("track__attachment_cover", "track__description")
            .order_by("-creation_date")
        )[:50]
        data = serializers.rss_serialize_channel_full(channel=object, uploads=uploads)
        return response.Response(data, status=200)

    @decorators.action(
        methods=["get"],
        detail=False,
        url_path="metadata-choices",
        url_name="metadata_choices",
        permission_classes=[],
    )
    def metedata_choices(self, request, *args, **kwargs):
        data = {
            "language": [
                {"value": code, "label": name} for code, name in locales.ISO_639_CHOICES
            ],
            "itunes_category": [
                {"value": code, "label": code, "children": children}
                for code, children in categories.ITUNES_CATEGORIES.items()
            ],
        }
        return response.Response(data)

    @decorators.action(
        methods=["post"],
        detail=False,
        url_path="rss-subscribe",
        url_name="rss_subscribe",
    )
    @transaction.atomic
    def rss_subscribe(self, request, *args, **kwargs):
        serializer = serializers.RssSubscribeSerializer(data=request.data)
        if not serializer.is_valid():
            return response.Response(serializer.errors, status=400)
        channel = (
            models.Channel.objects.filter(rss_url=serializer.validated_data["url"],)
            .order_by("id")
            .first()
        )
        if not channel:
            # try to retrieve the channel via its URL and create it
            try:
                channel, uploads = serializers.get_channel_from_rss_url(
                    serializer.validated_data["url"]
                )
            except serializers.FeedFetchException as e:
                return response.Response({"detail": str(e)}, status=400,)

        subscription = federation_models.Follow(actor=request.user.actor)
        subscription.fid = subscription.get_federation_id()
        subscription, created = SubscriptionsViewSet.queryset.get_or_create(
            target=channel.actor,
            actor=request.user.actor,
            defaults={
                "approved": True,
                "fid": subscription.fid,
                "uuid": subscription.uuid,
            },
        )
        # prefetch stuff
        subscription = SubscriptionsViewSet.queryset.get(pk=subscription.pk)

        return response.Response(
            serializers.SubscriptionSerializer(subscription).data, status=201
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["subscriptions_count"] = self.action in [
            "retrieve",
            "create",
            "update",
            "partial_update",
        ]
        if self.request.user.is_authenticated:
            context["actor"] = self.request.user.actor
        return context

    @transaction.atomic
    def perform_destroy(self, instance):
        instance.__class__.objects.filter(pk=instance.pk).delete()
        common_utils.on_commit(
            federation_tasks.remove_actor.delay, actor_id=instance.actor.pk
        )


class SubscriptionsViewSet(
    ChannelsMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "uuid"
    serializer_class = serializers.SubscriptionSerializer
    queryset = (
        federation_models.Follow.objects.exclude(target__channel__isnull=True)
        .prefetch_related(
            "target__channel__library",
            "target__channel__attributed_to",
            "actor",
            Prefetch("target__channel__artist", queryset=ARTIST_PREFETCH_QS),
        )
        .order_by("-creation_date")
    )
    permission_classes = [
        oauth_permissions.ScopePermission,
        rest_permissions.IsAuthenticated,
    ]
    required_scope = "libraries"
    anonymous_policy = False

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(actor=self.request.user.actor)

    @decorators.action(methods=["get"], detail=False)
    def all(self, request, *args, **kwargs):
        """
        Return all the subscriptions of the current user, with only limited data
        to have a performant endpoint and avoid lots of queries just to display
        subscription status in the UI
        """
        subscriptions = list(
            self.get_queryset().values_list("uuid", "target__channel__uuid")
        )

        payload = {
            "results": [{"uuid": str(u[0]), "channel": u[1]} for u in subscriptions],
            "count": len(subscriptions),
        }
        return response.Response(payload, status=200)

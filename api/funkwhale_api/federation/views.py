from django import forms
from django.conf import settings
from django.core import paginator
from django.db.models import Prefetch
from django.http import HttpResponse
from django.urls import reverse
from rest_framework import exceptions, mixins, permissions, response, viewsets
from rest_framework.decorators import action

from funkwhale_api.common import preferences
from funkwhale_api.common import utils as common_utils
from funkwhale_api.federation import utils as federation_utils
from funkwhale_api.moderation import models as moderation_models
from funkwhale_api.music import models as music_models
from funkwhale_api.music import utils as music_utils

from . import (
    actors,
    activity,
    authentication,
    models,
    renderers,
    serializers,
    utils,
    webfinger,
)


def redirect_to_html(public_url):
    response = HttpResponse(status=302)
    response["Location"] = common_utils.join_url(settings.FUNKWHALE_URL, public_url)
    return response


def get_collection_response(
    conf, querystring, collection_serializer, page_access_check=None
):
    page = querystring.get("page")
    if page is None:
        data = collection_serializer.data
    else:
        if page_access_check and not page_access_check():
            raise exceptions.AuthenticationFailed(
                "You do not have access to this resource"
            )
        try:
            page_number = int(page)
        except Exception:
            return response.Response({"page": ["Invalid page number"]}, status=400)
        conf["page_size"] = preferences.get("federation__collection_page_size")
        p = paginator.Paginator(conf["items"], conf["page_size"])
        try:
            page = p.page(page_number)
            conf["page"] = page
            serializer = serializers.CollectionPageSerializer(conf)
            data = serializer.data
        except paginator.EmptyPage:
            return response.Response(status=404)

    return response.Response(data)


class AuthenticatedIfAllowListEnabled(permissions.BasePermission):
    def has_permission(self, request, view):
        allow_list_enabled = preferences.get("moderation__allow_list_enabled")
        if not allow_list_enabled:
            return True
        return bool(request.actor)


class FederationMixin(object):
    permission_classes = [AuthenticatedIfAllowListEnabled]

    def dispatch(self, request, *args, **kwargs):
        if not preferences.get("federation__enabled"):
            return HttpResponse(status=405)
        return super().dispatch(request, *args, **kwargs)


class SharedViewSet(FederationMixin, viewsets.GenericViewSet):
    authentication_classes = [authentication.SignatureAuthentication]
    renderer_classes = renderers.get_ap_renderers()

    @action(
        methods=["post"],
        detail=False,
        content_negotiation_class=renderers.IgnoreClientContentNegotiation,
    )
    def inbox(self, request, *args, **kwargs):
        if request.method.lower() == "post" and request.actor is None:
            raise exceptions.AuthenticationFailed(
                "You need a valid signature to send an activity"
            )
        if request.method.lower() == "post":
            activity.receive(activity=request.data, on_behalf_of=request.actor)
        return response.Response({}, status=200)


class ActorViewSet(FederationMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    lookup_field = "preferred_username"
    authentication_classes = [authentication.SignatureAuthentication]
    renderer_classes = renderers.get_ap_renderers()
    queryset = (
        models.Actor.objects.local()
        .select_related("user", "channel__artist", "channel__attributed_to")
        .prefetch_related("channel__artist__tagged_items__tag")
    )
    serializer_class = serializers.ActorSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.exclude(channel__attributed_to=actors.get_service_actor())

    def get_permissions(self):
        # cf #1999 it must be possible to fetch actors without being authenticated
        # otherwise we end up in a loop
        if self.action == "retrieve":
            return []
        return super().get_permissions()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if utils.should_redirect_ap_to_html(request.headers.get("accept")):
            if instance.get_channel():
                return redirect_to_html(instance.channel.get_absolute_url())
            return redirect_to_html(instance.get_absolute_url())

        serializer = self.get_serializer(instance)
        return response.Response(serializer.data)

    @action(
        methods=["get", "post"],
        detail=True,
        content_negotiation_class=renderers.IgnoreClientContentNegotiation,
    )
    def inbox(self, request, *args, **kwargs):
        inbox_actor = self.get_object()
        if request.method.lower() == "post" and request.actor is None:
            raise exceptions.AuthenticationFailed(
                "You need a valid signature to send an activity"
            )
        if request.method.lower() == "post":
            activity.receive(
                activity=request.data,
                on_behalf_of=request.actor,
                inbox_actor=inbox_actor,
            )
        return response.Response({}, status=200)

    @action(methods=["get", "post"], detail=True)
    def outbox(self, request, *args, **kwargs):
        actor = self.get_object()
        channel = actor.get_channel()
        if channel:
            return self.get_channel_outbox_response(request, channel)
        return response.Response({}, status=200)

    def get_channel_outbox_response(self, request, channel):
        conf = {
            "id": channel.actor.outbox_url,
            "actor": channel.actor,
            "items": channel.library.uploads.for_federation()
            .order_by("-creation_date")
            .prefetch_related("library__channel__actor", "track__artist"),
            "item_serializer": serializers.ChannelCreateUploadSerializer,
        }
        return get_collection_response(
            conf=conf,
            querystring=request.GET,
            collection_serializer=serializers.ChannelOutboxSerializer(channel),
        )

    @action(methods=["get"], detail=True)
    def followers(self, request, *args, **kwargs):
        self.get_object()
        # XXX to implement
        return response.Response({})

    @action(methods=["get"], detail=True)
    def following(self, request, *args, **kwargs):
        self.get_object()
        # XXX to implement
        return response.Response({})


class EditViewSet(FederationMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    lookup_field = "uuid"
    authentication_classes = [authentication.SignatureAuthentication]
    renderer_classes = renderers.get_ap_renderers()
    # queryset = common_models.Mutation.objects.local().select_related()
    # serializer_class = serializers.ActorSerializer


class ReportViewSet(
    FederationMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    lookup_field = "uuid"
    authentication_classes = [authentication.SignatureAuthentication]
    renderer_classes = renderers.get_ap_renderers()
    queryset = moderation_models.Report.objects.none()


class WellKnownViewSet(viewsets.GenericViewSet):
    authentication_classes = []
    permission_classes = []
    renderer_classes = [renderers.JSONRenderer, renderers.WebfingerRenderer]

    @action(methods=["get"], detail=False)
    def nodeinfo(self, request, *args, **kwargs):
        data = {
            "links": [
                {
                    "rel": "http://nodeinfo.diaspora.software/ns/schema/2.0",
                    "href": utils.full_url(reverse("api:v1:instance:nodeinfo-2.0")),
                }
            ]
        }
        return response.Response(data)

    @action(methods=["get"], detail=False)
    def webfinger(self, request, *args, **kwargs):
        if not preferences.get("federation__enabled"):
            return HttpResponse(status=405)
        try:
            resource_type, resource = webfinger.clean_resource(request.GET["resource"])
            cleaner = getattr(webfinger, "clean_{}".format(resource_type))
            result = cleaner(resource)
            handler = getattr(self, "handler_{}".format(resource_type))
            data = handler(result)
        except forms.ValidationError as e:
            return response.Response({"errors": {"resource": e.message}}, status=400)
        except KeyError:
            return response.Response(
                {"errors": {"resource": "This field is required"}}, status=400
            )

        return response.Response(data)

    def handler_acct(self, clean_result):
        username, hostname = clean_result

        try:
            actor = models.Actor.objects.local().get(preferred_username=username)
        except models.Actor.DoesNotExist:
            raise forms.ValidationError("Invalid username")

        return serializers.ActorWebfingerSerializer(actor).data


def has_library_access(request, library):
    if library.privacy_level == "everyone":
        return True
    if request.user.is_authenticated and request.user.is_superuser:
        return True

    try:
        actor = request.actor
    except AttributeError:
        return False

    return library.received_follows.filter(actor=actor, approved=True).exists()


class MusicLibraryViewSet(
    FederationMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    authentication_classes = [authentication.SignatureAuthentication]
    renderer_classes = renderers.get_ap_renderers()
    serializer_class = serializers.LibrarySerializer
    queryset = (
        music_models.Library.objects.all()
        .local()
        .select_related("actor")
        .filter(channel=None)
    )
    lookup_field = "uuid"

    def retrieve(self, request, *args, **kwargs):
        lb = self.get_object()
        if utils.should_redirect_ap_to_html(request.headers.get("accept")):
            return redirect_to_html(lb.get_absolute_url())
        conf = {
            "id": lb.get_federation_id(),
            "actor": lb.actor,
            "name": lb.name,
            "summary": lb.description,
            "items": lb.uploads.for_federation()
            .order_by("-creation_date")
            .prefetch_related(
                Prefetch(
                    "track",
                    queryset=music_models.Track.objects.select_related(
                        "album__artist__attributed_to",
                        "artist__attributed_to",
                        "artist__attachment_cover",
                        "attachment_cover",
                        "album__attributed_to",
                        "attributed_to",
                        "album__attachment_cover",
                        "album__artist__attachment_cover",
                        "description",
                    ).prefetch_related(
                        "tagged_items__tag",
                        "album__tagged_items__tag",
                        "album__artist__tagged_items__tag",
                        "artist__tagged_items__tag",
                        "artist__description",
                        "album__description",
                    ),
                )
            ),
            "item_serializer": serializers.UploadSerializer,
        }

        return get_collection_response(
            conf=conf,
            querystring=request.GET,
            collection_serializer=serializers.LibrarySerializer(lb),
            page_access_check=lambda: has_library_access(request, lb),
        )

    @action(methods=["get"], detail=True)
    def followers(self, request, *args, **kwargs):
        self.get_object()
        # XXX Implement this
        return response.Response({})


class MusicUploadViewSet(
    FederationMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    authentication_classes = [authentication.SignatureAuthentication]
    renderer_classes = renderers.get_ap_renderers()
    queryset = music_models.Upload.objects.local().select_related(
        "library__actor",
        "track__artist",
        "track__album__artist",
        "track__description",
        "track__album__attachment_cover",
        "track__album__artist__attachment_cover",
        "track__artist__attachment_cover",
        "track__attachment_cover",
    )
    serializer_class = serializers.UploadSerializer
    lookup_field = "uuid"

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if utils.should_redirect_ap_to_html(request.headers.get("accept")):
            return redirect_to_html(instance.track.get_absolute_url())

        serializer = self.get_serializer(instance)
        return response.Response(serializer.data)

    def get_queryset(self):
        queryset = super().get_queryset()
        actor = music_utils.get_actor_from_request(self.request)
        return queryset.playable_by(actor)

    def get_serializer(self, obj):
        if obj.library.get_channel():
            return serializers.ChannelUploadSerializer(obj)
        return super().get_serializer(obj)

    @action(
        methods=["get"],
        detail=True,
        content_negotiation_class=renderers.IgnoreClientContentNegotiation,
    )
    def activity(self, request, *args, **kwargs):
        object = self.get_object()
        serializer = serializers.ChannelCreateUploadSerializer(object)
        return response.Response(serializer.data)


class MusicArtistViewSet(
    FederationMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    authentication_classes = [authentication.SignatureAuthentication]
    renderer_classes = renderers.get_ap_renderers()
    queryset = music_models.Artist.objects.local().select_related(
        "description", "attachment_cover"
    )
    serializer_class = serializers.ArtistSerializer
    lookup_field = "uuid"

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if utils.should_redirect_ap_to_html(request.headers.get("accept")):
            return redirect_to_html(instance.get_absolute_url())

        serializer = self.get_serializer(instance)
        return response.Response(serializer.data)


class MusicAlbumViewSet(
    FederationMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    authentication_classes = [authentication.SignatureAuthentication]
    renderer_classes = renderers.get_ap_renderers()
    queryset = music_models.Album.objects.local().select_related(
        "artist__description", "description", "artist__attachment_cover"
    )
    serializer_class = serializers.AlbumSerializer
    lookup_field = "uuid"

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if utils.should_redirect_ap_to_html(request.headers.get("accept")):
            return redirect_to_html(instance.get_absolute_url())

        serializer = self.get_serializer(instance)
        return response.Response(serializer.data)


class MusicTrackViewSet(
    FederationMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    authentication_classes = [authentication.SignatureAuthentication]
    renderer_classes = renderers.get_ap_renderers()
    queryset = music_models.Track.objects.local().select_related(
        "album__artist",
        "album__description",
        "artist__description",
        "description",
        "attachment_cover",
        "album__artist__attachment_cover",
        "album__attachment_cover",
        "artist__attachment_cover",
    )
    serializer_class = serializers.TrackSerializer
    lookup_field = "uuid"

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if utils.should_redirect_ap_to_html(request.headers.get("accept")):
            return redirect_to_html(instance.get_absolute_url())

        serializer = self.get_serializer(instance)
        return response.Response(serializer.data)


class ChannelViewSet(
    FederationMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    authentication_classes = [authentication.SignatureAuthentication]
    renderer_classes = renderers.get_ap_renderers()
    queryset = music_models.Artist.objects.local().select_related(
        "description", "attachment_cover"
    )
    serializer_class = serializers.ArtistSerializer
    lookup_field = "uuid"

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if utils.should_redirect_ap_to_html(request.headers.get("accept")):
            return redirect_to_html(instance.get_absolute_url())

        serializer = self.get_serializer(instance)
        return response.Response(serializer.data)


class IndexViewSet(FederationMixin, viewsets.GenericViewSet):
    authentication_classes = [authentication.SignatureAuthentication]
    renderer_classes = renderers.get_ap_renderers()

    def dispatch(self, request, *args, **kwargs):
        if not preferences.get("federation__public_index"):
            return HttpResponse(status=405)
        return super().dispatch(request, *args, **kwargs)

    @action(
        methods=["get"], detail=False,
    )
    def libraries(self, request, *args, **kwargs):
        libraries = (
            music_models.Library.objects.local()
            .filter(channel=None, privacy_level="everyone")
            .prefetch_related("actor")
            .order_by("creation_date")
        )
        conf = {
            "id": federation_utils.full_url(
                reverse("federation:index:index-libraries")
            ),
            "items": libraries,
            "item_serializer": serializers.LibrarySerializer,
            "page_size": 100,
            "actor": None,
        }
        return get_collection_response(
            conf=conf,
            querystring=request.GET,
            collection_serializer=serializers.IndexSerializer(conf),
        )

        return response.Response({}, status=200)

    @action(
        methods=["get"], detail=False,
    )
    def channels(self, request, *args, **kwargs):
        actors = (
            models.Actor.objects.local()
            .exclude(channel=None)
            .order_by("channel__creation_date")
            .prefetch_related(
                "channel__attributed_to",
                "channel__artist",
                "channel__artist__description",
                "channel__artist__attachment_cover",
            )
        )
        conf = {
            "id": federation_utils.full_url(reverse("federation:index:index-channels")),
            "items": actors,
            "item_serializer": serializers.ActorSerializer,
            "page_size": 100,
            "actor": None,
        }
        return get_collection_response(
            conf=conf,
            querystring=request.GET,
            collection_serializer=serializers.IndexSerializer(conf),
        )

        return response.Response({}, status=200)

"""
Documentation of Subsonic API can be found at http://www.subsonic.org/pages/api.jsp
"""
import datetime
import functools

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from rest_framework import exceptions
from rest_framework import permissions as rest_permissions
from rest_framework import renderers, response, viewsets
from rest_framework.decorators import action
from rest_framework.serializers import ValidationError

import funkwhale_api
from funkwhale_api.activity import record
from funkwhale_api.audio import models as audio_models
from funkwhale_api.audio import serializers as audio_serializers
from funkwhale_api.audio import views as audio_views
from funkwhale_api.common import (
    fields,
    preferences,
    models as common_models,
    utils as common_utils,
    tasks as common_tasks,
)
from funkwhale_api.federation import models as federation_models
from funkwhale_api.favorites.models import TrackFavorite
from funkwhale_api.moderation import filters as moderation_filters
from funkwhale_api.music import models as music_models
from funkwhale_api.music import serializers as music_serializers
from funkwhale_api.music import utils
from funkwhale_api.music import views as music_views
from funkwhale_api.playlists import models as playlists_models
from funkwhale_api.tags import models as tags_models
from funkwhale_api.users import models as users_models

from . import authentication, filters, negotiation, serializers


def find_object(
    queryset, model_field="pk", field="id", cast=int, filter_playable=False
):
    def decorator(func):
        @functools.wraps(func)
        def inner(self, request, *args, **kwargs):
            data = request.GET or request.POST
            try:
                raw_value = data[field]
            except KeyError:
                return response.Response(
                    {
                        "error": {
                            "code": 10,
                            "message": "required parameter '{}' not present".format(
                                field
                            ),
                        }
                    }
                )
            try:
                value = cast(raw_value)
            except (ValueError, TypeError, ValidationError):
                return response.Response(
                    {
                        "error": {
                            "code": 0,
                            "message": 'For input string "{}"'.format(raw_value),
                        }
                    }
                )
            qs = queryset
            if hasattr(qs, "__call__"):
                qs = qs(request)

            if filter_playable:
                actor = utils.get_actor_from_request(request)
                qs = qs.playable_by(actor)

            try:
                obj = qs.get(**{model_field: value})
            except qs.model.DoesNotExist:
                return response.Response(
                    {
                        "error": {
                            "code": 70,
                            "message": "{} not found".format(qs.model.__name__),
                        }
                    }
                )
            kwargs["obj"] = obj
            return func(self, request, *args, **kwargs)

        return inner

    return decorator


def get_playlist_qs(request):
    qs = playlists_models.Playlist.objects.filter(
        fields.privacy_level_query(request.user)
    )
    qs = qs.with_tracks_count().exclude(_tracks_count=0).select_related("user")
    return qs.order_by("-creation_date")


def requires_channels(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        if not preferences.get("audio__channels_enabled"):
            payload = {
                "error": {
                    "code": 0,
                    "message": "Channels / podcasts are disabled on this pod",
                }
            }
            return response.Response(payload, status=405)
        return f(*args, **kwargs)

    return inner


class SubsonicViewSet(viewsets.GenericViewSet):
    content_negotiation_class = negotiation.SubsonicContentNegociation
    authentication_classes = [authentication.SubsonicAuthentication]
    permission_classes = [rest_permissions.IsAuthenticated]
    throttling_scopes = {"*": {"authenticated": "subsonic", "anonymous": "subsonic"}}

    def dispatch(self, request, *args, **kwargs):
        if not preferences.get("subsonic__enabled"):
            r = response.Response({}, status=405)
            r.accepted_renderer = renderers.JSONRenderer()
            r.accepted_media_type = "application/json"
            r.renderer_context = {}
            return r
        return super().dispatch(request, *args, **kwargs)

    def handle_exception(self, exc):
        # subsonic API sends 200 status code with custom error
        # codes in the payload
        mapping = {
            exceptions.AuthenticationFailed: (40, "Wrong username or password."),
            exceptions.NotAuthenticated: (10, "Required parameter is missing."),
        }
        payload = {"status": "failed"}
        if exc.__class__ in mapping:
            code, message = mapping[exc.__class__]
        else:
            return super().handle_exception(exc)
        payload["error"] = {"code": code, "message": message}

        return response.Response(payload, status=200)

    @action(detail=False, methods=["get", "post"], permission_classes=[])
    def ping(self, request, *args, **kwargs):
        data = {"status": "ok", "version": "1.16.0"}
        return response.Response(data, status=200)

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="get_license",
        permission_classes=[],
        url_path="getLicense",
    )
    def get_license(self, request, *args, **kwargs):
        now = timezone.now()
        data = {
            "status": "ok",
            "version": "1.16.0",
            "type": "funkwhale",
            "funkwhaleVersion": funkwhale_api.__version__,
            "license": {
                "valid": "true",
                "email": "valid@valid.license",
                "licenseExpires": now + datetime.timedelta(days=365),
            },
        }
        return response.Response(data, status=200)

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="get_artists",
        url_path="getArtists",
    )
    def get_artists(self, request, *args, **kwargs):
        artists = (
            music_models.Artist.objects.all()
            .exclude(
                moderation_filters.get_filtered_content_query(
                    moderation_filters.USER_FILTER_CONFIG["ARTIST"], request.user
                )
            )
            .playable_by(utils.get_actor_from_request(request))
        )
        data = serializers.GetArtistsSerializer(artists).data
        payload = {"artists": data}

        return response.Response(payload, status=200)

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="get_indexes",
        url_path="getIndexes",
    )
    def get_indexes(self, request, *args, **kwargs):
        artists = (
            music_models.Artist.objects.all()
            .exclude(
                moderation_filters.get_filtered_content_query(
                    moderation_filters.USER_FILTER_CONFIG["ARTIST"], request.user
                )
            )
            .playable_by(utils.get_actor_from_request(request))
        )
        data = serializers.GetArtistsSerializer(artists).data
        payload = {"indexes": data}

        return response.Response(payload, status=200)

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="get_artist",
        url_path="getArtist",
    )
    @find_object(music_models.Artist.objects.all(), filter_playable=True)
    def get_artist(self, request, *args, **kwargs):
        artist = kwargs.pop("obj")
        data = serializers.GetArtistSerializer(artist).data
        payload = {"artist": data}

        return response.Response(payload, status=200)

    @action(
        detail=False, methods=["get", "post"], url_name="get_song", url_path="getSong"
    )
    @find_object(music_models.Track.objects.all(), filter_playable=True)
    def get_song(self, request, *args, **kwargs):
        track = kwargs.pop("obj")
        data = serializers.GetSongSerializer(track).data
        payload = {"song": data}

        return response.Response(payload, status=200)

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="get_artist_info2",
        url_path="getArtistInfo2",
    )
    @find_object(music_models.Artist.objects.all(), filter_playable=True)
    def get_artist_info2(self, request, *args, **kwargs):
        payload = {"artist-info2": {}}

        return response.Response(payload, status=200)

    @action(
        detail=False, methods=["get", "post"], url_name="get_album", url_path="getAlbum"
    )
    @find_object(
        music_models.Album.objects.select_related("artist"), filter_playable=True
    )
    def get_album(self, request, *args, **kwargs):
        album = kwargs.pop("obj")
        data = serializers.GetAlbumSerializer(album).data
        payload = {"album": data}
        return response.Response(payload, status=200)

    @action(detail=False, methods=["get", "post"], url_name="stream", url_path="stream")
    @find_object(music_models.Track.objects.all(), filter_playable=True)
    def stream(self, request, *args, **kwargs):
        data = request.GET or request.POST
        track = kwargs.pop("obj")
        queryset = track.uploads.select_related("track__album__artist", "track__artist")
        sorted_uploads = music_serializers.sort_uploads_for_listen(queryset)

        if not sorted_uploads:
            return response.Response(status=404)

        upload = sorted_uploads[0]

        max_bitrate = data.get("maxBitRate")
        try:
            max_bitrate = min(max(int(max_bitrate), 0), 320) or None
        except (TypeError, ValueError):
            max_bitrate = None

        if max_bitrate:
            max_bitrate = max_bitrate * 1000

        format = data.get("format") or None
        if max_bitrate and not format:
            # specific bitrate requested, but no format specified
            # so we use a default one, cf #867. This helps with clients
            # that don't send the format parameter, such as DSub.
            format = settings.SUBSONIC_DEFAULT_TRANSCODING_FORMAT
        elif format == "raw":
            format = None

        return music_views.handle_serve(
            upload=upload,
            user=request.user,
            format=format,
            max_bitrate=max_bitrate,
            # Subsonic clients don't expect 302 redirection unfortunately,
            # So we have to proxy media files
            proxy_media=True,
            wsgi_request=request._request,
        )

    @action(detail=False, methods=["get", "post"], url_name="star", url_path="star")
    @find_object(music_models.Track.objects.all())
    def star(self, request, *args, **kwargs):
        track = kwargs.pop("obj")
        TrackFavorite.add(user=request.user, track=track)
        return response.Response({"status": "ok"})

    @action(detail=False, methods=["get", "post"], url_name="unstar", url_path="unstar")
    @find_object(music_models.Track.objects.all())
    def unstar(self, request, *args, **kwargs):
        track = kwargs.pop("obj")
        request.user.track_favorites.filter(track=track).delete()
        return response.Response({"status": "ok"})

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="get_starred2",
        url_path="getStarred2",
    )
    def get_starred2(self, request, *args, **kwargs):
        favorites = request.user.track_favorites.all()
        data = {"starred2": {"song": serializers.get_starred_tracks_data(favorites)}}
        return response.Response(data)

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="get_random_songs",
        url_path="getRandomSongs",
    )
    def get_random_songs(self, request, *args, **kwargs):
        data = request.GET or request.POST
        actor = utils.get_actor_from_request(request)
        queryset = music_models.Track.objects.all().exclude(
            moderation_filters.get_filtered_content_query(
                moderation_filters.USER_FILTER_CONFIG["TRACK"], request.user
            )
        )
        queryset = queryset.playable_by(actor)
        try:
            size = int(data["size"])
        except (TypeError, KeyError, ValueError):
            size = 50

        queryset = (
            queryset.playable_by(actor).prefetch_related("uploads").order_by("?")[:size]
        )
        data = {
            "randomSongs": {
                "song": serializers.GetSongSerializer(queryset, many=True).data
            }
        }
        return response.Response(data)

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="get_songs_by_genre",
        url_path="getSongsByGenre",
    )
    def get_songs_by_genre(self, request, *args, **kwargs):
        data = request.GET or request.POST
        actor = utils.get_actor_from_request(request)
        queryset = music_models.Track.objects.all().exclude(
            moderation_filters.get_filtered_content_query(
                moderation_filters.USER_FILTER_CONFIG["TRACK"], request.user
            )
        )
        queryset = queryset.playable_by(actor)
        try:
            offset = int(data.get("offset", 0))
        except (TypeError, ValueError):

            offset = 0

        try:
            size = int(
                data["count"]
            )  # yep. Some endpoints have size, other have count…
        except (TypeError, KeyError, ValueError):
            size = 50

        genre = data.get("genre")
        queryset = (
            queryset.playable_by(actor)
            .filter(
                Q(tagged_items__tag__name=genre)
                | Q(artist__tagged_items__tag__name=genre)
                | Q(album__artist__tagged_items__tag__name=genre)
                | Q(album__tagged_items__tag__name=genre)
            )
            .prefetch_related("uploads")
            .distinct()
            .order_by("-creation_date")[offset : offset + size]
        )
        data = {
            "songsByGenre": {
                "song": serializers.GetSongSerializer(queryset, many=True).data
            }
        }
        return response.Response(data)

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="get_starred",
        url_path="getStarred",
    )
    def get_starred(self, request, *args, **kwargs):
        favorites = request.user.track_favorites.all()
        data = {"starred": {"song": serializers.get_starred_tracks_data(favorites)}}
        return response.Response(data)

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="get_album_list2",
        url_path="getAlbumList2",
    )
    def get_album_list2(self, request, *args, **kwargs):
        queryset = (
            music_models.Album.objects.exclude(
                moderation_filters.get_filtered_content_query(
                    moderation_filters.USER_FILTER_CONFIG["ALBUM"], request.user
                )
            )
            .with_tracks_count()
            .order_by("artist__name")
        )
        data = request.GET or request.POST
        filterset = filters.AlbumList2FilterSet(data, queryset=queryset)
        queryset = filterset.qs
        actor = utils.get_actor_from_request(request)
        queryset = queryset.playable_by(actor)
        type = data.get("type", "alphabeticalByArtist")

        if type == "alphabeticalByArtist":
            queryset = queryset.order_by("artist__name")
        elif type == "random":
            queryset = queryset.order_by("?")
        elif type == "alphabeticalByName" or not type:
            queryset = queryset.order_by("artist__title")
        elif type == "recent" or not type:
            queryset = queryset.exclude(release_date=None).order_by("-release_date")
        elif type == "newest" or not type:
            queryset = queryset.order_by("-creation_date")
        elif type == "byGenre" and data.get("genre"):
            genre = data.get("genre")
            queryset = queryset.filter(
                Q(tagged_items__tag__name=genre)
                | Q(artist__tagged_items__tag__name=genre)
            )
        elif type == "byYear":
            try:
                boundaries = [
                    int(data.get("fromYear", 0)),
                    int(data.get("toYear", 99999999)),
                ]

            except (TypeError, ValueError):
                return response.Response(
                    {
                        "error": {
                            "code": 10,
                            "message": "Invalid fromYear or toYear parameter",
                        }
                    }
                )
            # because, yeah, the specification explicitly state that fromYear can be greater
            # than toYear, to indicate reverse ordering…
            # http://www.subsonic.org/pages/api.jsp#getAlbumList2
            from_year = min(boundaries)
            to_year = max(boundaries)
            queryset = queryset.filter(
                release_date__year__gte=from_year, release_date__year__lte=to_year
            )
            if boundaries[0] <= boundaries[1]:
                queryset = queryset.order_by("release_date")
            else:
                queryset = queryset.order_by("-release_date")
        try:
            offset = int(data["offset"])
        except (TypeError, KeyError, ValueError):
            offset = 0

        try:
            size = int(data["size"])
        except (TypeError, KeyError, ValueError):
            size = 50

        size = min(size, 500)
        queryset = queryset[offset : offset + size]
        data = {"albumList2": {"album": serializers.get_album_list2_data(queryset)}}
        return response.Response(data)

    @action(
        detail=False, methods=["get", "post"], url_name="search3", url_path="search3"
    )
    def search3(self, request, *args, **kwargs):
        data = request.GET or request.POST
        query = str(data.get("query", "")).replace("*", "")
        actor = utils.get_actor_from_request(request)
        conf = [
            {
                "subsonic": "artist",
                "search_fields": ["name"],
                "queryset": (
                    music_models.Artist.objects.with_albums_count().values(
                        "id", "_albums_count", "name"
                    )
                ),
                "serializer": lambda qs: [serializers.get_artist_data(a) for a in qs],
            },
            {
                "subsonic": "album",
                "search_fields": ["title"],
                "queryset": (
                    music_models.Album.objects.with_tracks_count().select_related(
                        "artist"
                    )
                ),
                "serializer": serializers.get_album_list2_data,
            },
            {
                "subsonic": "song",
                "search_fields": ["title"],
                "queryset": (
                    music_models.Track.objects.prefetch_related(
                        "uploads"
                    ).select_related("album__artist")
                ),
                "serializer": serializers.get_song_list_data,
            },
        ]
        payload = {"searchResult3": {}}
        for c in conf:
            offsetKey = "{}Offset".format(c["subsonic"])
            countKey = "{}Count".format(c["subsonic"])
            try:
                offset = int(data[offsetKey])
            except (TypeError, KeyError, ValueError):
                offset = 0

            try:
                size = int(data[countKey])
            except (TypeError, KeyError, ValueError):
                size = 20

            size = min(size, 100)
            queryset = c["queryset"]
            if query:
                queryset = c["queryset"].filter(
                    utils.get_query(query, c["search_fields"])
                )
            queryset = queryset.playable_by(actor)
            queryset = common_utils.order_for_search(queryset, c["search_fields"][0])
            queryset = queryset[offset : offset + size]
            payload["searchResult3"][c["subsonic"]] = c["serializer"](queryset)
        return response.Response(payload)

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="get_playlists",
        url_path="getPlaylists",
    )
    def get_playlists(self, request, *args, **kwargs):
        qs = get_playlist_qs(request)
        data = {
            "playlists": {"playlist": [serializers.get_playlist_data(p) for p in qs]}
        }
        return response.Response(data)

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="get_playlist",
        url_path="getPlaylist",
    )
    @find_object(lambda request: get_playlist_qs(request))
    def get_playlist(self, request, *args, **kwargs):
        playlist = kwargs.pop("obj")
        data = {"playlist": serializers.get_playlist_detail_data(playlist)}
        return response.Response(data)

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="update_playlist",
        url_path="updatePlaylist",
    )
    @find_object(lambda request: request.user.playlists.all(), field="playlistId")
    def update_playlist(self, request, *args, **kwargs):
        playlist = kwargs.pop("obj")
        data = request.GET or request.POST
        new_name = data.get("name", "")
        if new_name:
            playlist.name = new_name
            playlist.save(update_fields=["name", "modification_date"])
        try:
            to_remove = int(data["songIndexToRemove"])
            plt = playlist.playlist_tracks.get(index=to_remove)
        except (TypeError, ValueError, KeyError):
            pass
        except playlists_models.PlaylistTrack.DoesNotExist:
            pass
        else:
            plt.delete(update_indexes=True)

        ids = []
        for i in data.getlist("songIdToAdd"):
            try:
                ids.append(int(i))
            except (TypeError, ValueError):
                pass
        if ids:
            tracks = music_models.Track.objects.filter(pk__in=ids)
            by_id = {t.id: t for t in tracks}
            sorted_tracks = []
            for i in ids:
                try:
                    sorted_tracks.append(by_id[i])
                except KeyError:
                    pass
            if sorted_tracks:
                playlist.insert_many(sorted_tracks)

        data = {"status": "ok"}
        return response.Response(data)

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="delete_playlist",
        url_path="deletePlaylist",
    )
    @find_object(lambda request: request.user.playlists.all())
    def delete_playlist(self, request, *args, **kwargs):
        playlist = kwargs.pop("obj")
        playlist.delete()
        data = {"status": "ok"}
        return response.Response(data)

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="create_playlist",
        url_path="createPlaylist",
    )
    def create_playlist(self, request, *args, **kwargs):
        data = request.GET or request.POST
        name = data.get("name", "")
        if not name:
            return response.Response(
                {
                    "error": {
                        "code": 10,
                        "message": "Playlist ID or name must be specified.",
                    }
                }
            )

        playlist = request.user.playlists.create(name=name)
        ids = []
        for i in data.getlist("songId"):
            try:
                ids.append(int(i))
            except (TypeError, ValueError):
                pass

        if ids:
            tracks = music_models.Track.objects.filter(pk__in=ids)
            by_id = {t.id: t for t in tracks}
            sorted_tracks = []
            for i in ids:
                try:
                    sorted_tracks.append(by_id[i])
                except KeyError:
                    pass
            if sorted_tracks:
                playlist.insert_many(sorted_tracks)
        playlist = request.user.playlists.with_tracks_count().get(pk=playlist.pk)
        data = {"playlist": serializers.get_playlist_detail_data(playlist)}
        return response.Response(data)

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="get_avatar",
        url_path="getAvatar",
    )
    @find_object(
        queryset=users_models.User.objects.exclude(avatar=None).exclude(avatar=""),
        model_field="username__iexact",
        field="username",
        cast=str,
    )
    def get_avatar(self, request, *args, **kwargs):
        user = kwargs.pop("obj")
        mapping = {"nginx": "X-Accel-Redirect", "apache2": "X-Sendfile"}
        path = music_views.get_file_path(user.avatar)
        file_header = mapping[settings.REVERSE_PROXY_TYPE]
        # let the proxy set the content-type
        r = response.Response({}, content_type="")
        r[file_header] = path
        return r

    @action(
        detail=False, methods=["get", "post"], url_name="get_user", url_path="getUser"
    )
    @find_object(
        queryset=lambda request: users_models.User.objects.filter(pk=request.user.pk),
        model_field="username__iexact",
        field="username",
        cast=str,
    )
    def get_user(self, request, *args, **kwargs):
        data = {"user": serializers.get_user_detail_data(request.user)}
        return response.Response(data)

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="get_music_folders",
        url_path="getMusicFolders",
    )
    def get_music_folders(self, request, *args, **kwargs):
        data = {"musicFolders": {"musicFolder": [{"id": 1, "name": "Music"}]}}
        return response.Response(data)

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="get_cover_art",
        url_path="getCoverArt",
    )
    def get_cover_art(self, request, *args, **kwargs):
        data = request.GET or request.POST
        id = data.get("id", "")
        if not id:
            return response.Response(
                {"error": {"code": 10, "message": "cover art ID must be specified."}}
            )

        if id.startswith("al-"):
            try:
                album_id = int(id.replace("al-", ""))
                album = (
                    music_models.Album.objects.exclude(attachment_cover=None)
                    .select_related("attachment_cover")
                    .get(pk=album_id)
                )
            except (TypeError, ValueError, music_models.Album.DoesNotExist):
                return response.Response(
                    {"error": {"code": 70, "message": "cover art not found."}}
                )
            attachment = album.attachment_cover
        elif id.startswith("at-"):
            try:
                attachment_id = id.replace("at-", "")
                attachment = common_models.Attachment.objects.get(uuid=attachment_id)
            except (TypeError, ValueError, music_models.Album.DoesNotExist):
                return response.Response(
                    {"error": {"code": 70, "message": "cover art not found."}}
                )
        else:
            return response.Response(
                {"error": {"code": 70, "message": "cover art not found."}}
            )

        if not attachment.file:
            common_tasks.fetch_remote_attachment(attachment)
        cover = attachment.file
        mapping = {"nginx": "X-Accel-Redirect", "apache2": "X-Sendfile"}
        path = music_views.get_file_path(cover)
        file_header = mapping[settings.REVERSE_PROXY_TYPE]
        # let the proxy set the content-type
        r = response.Response({}, content_type="")
        r[file_header] = path
        return r

    @action(
        detail=False, methods=["get", "post"], url_name="scrobble", url_path="scrobble"
    )
    def scrobble(self, request, *args, **kwargs):
        data = request.GET or request.POST
        serializer = serializers.ScrobbleSerializer(
            data=data, context={"user": request.user}
        )
        if not serializer.is_valid():
            return response.Response(
                {"error": {"code": 0, "message": "Invalid payload"}}
            )
        if serializer.validated_data["submission"]:
            listening = serializer.save()
            record.send(listening)
        return response.Response({})

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="get_genres",
        url_path="getGenres",
    )
    def get_genres(self, request, *args, **kwargs):
        album_ct = ContentType.objects.get_for_model(music_models.Album)
        track_ct = ContentType.objects.get_for_model(music_models.Track)
        queryset = (
            tags_models.Tag.objects.annotate(
                _albums_count=Count(
                    "tagged_items", filter=Q(tagged_items__content_type=album_ct)
                ),
                _tracks_count=Count(
                    "tagged_items", filter=Q(tagged_items__content_type=track_ct)
                ),
            )
            .exclude(_tracks_count=0, _albums_count=0)
            .order_by("name")
        )
        data = {
            "genres": {"genre": [serializers.get_genre_data(tag) for tag in queryset]}
        }
        return response.Response(data)

    # podcast related views
    @action(
        detail=False,
        methods=["get", "post"],
        url_name="create_podcast_channel",
        url_path="createPodcastChannel",
    )
    @requires_channels
    @transaction.atomic
    def create_podcast_channel(self, request, *args, **kwargs):
        data = request.GET or request.POST
        serializer = audio_serializers.RssSubscribeSerializer(data=data)
        if not serializer.is_valid():
            return response.Response({"error": {"code": 0, "message": "invalid url"}})
        channel = (
            audio_models.Channel.objects.filter(
                rss_url=serializer.validated_data["url"],
            )
            .order_by("id")
            .first()
        )
        if not channel:
            # try to retrieve the channel via its URL and create it
            try:
                channel, uploads = audio_serializers.get_channel_from_rss_url(
                    serializer.validated_data["url"]
                )
            except audio_serializers.FeedFetchException as e:
                return response.Response(
                    {
                        "error": {
                            "code": 0,
                            "message": "Error while fetching url: {}".format(e),
                        }
                    }
                )

        subscription = federation_models.Follow(actor=request.user.actor)
        subscription.fid = subscription.get_federation_id()
        audio_views.SubscriptionsViewSet.queryset.get_or_create(
            target=channel.actor,
            actor=request.user.actor,
            defaults={
                "approved": True,
                "fid": subscription.fid,
                "uuid": subscription.uuid,
            },
        )
        return response.Response({"status": "ok"})

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="delete_podcast_channel",
        url_path="deletePodcastChannel",
    )
    @requires_channels
    @find_object(
        audio_models.Channel.objects.all().select_related("actor"),
        model_field="uuid",
        field="id",
        cast=str,
    )
    def delete_podcast_channel(self, request, *args, **kwargs):
        channel = kwargs.pop("obj")
        actor = request.user.actor
        actor.emitted_follows.filter(target=channel.actor).delete()
        return response.Response({"status": "ok"})

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="get_podcasts",
        url_path="getPodcasts",
    )
    @requires_channels
    def get_podcasts(self, request, *args, **kwargs):
        data = request.GET or request.POST
        id = data.get("id")
        channels = audio_models.Channel.objects.subscribed(request.user.actor)
        if id:
            channels = channels.filter(uuid=id)
        channels = channels.select_related(
            "artist__attachment_cover", "artist__description", "library", "actor"
        )
        uploads_qs = (
            music_models.Upload.objects.playable_by(request.user.actor)
            .select_related("track__attachment_cover", "track__description",)
            .order_by("-track__creation_date")
        )

        if data.get("includeEpisodes", "true") == "true":
            channels = channels.prefetch_related(
                Prefetch(
                    "library__uploads",
                    queryset=uploads_qs,
                    to_attr="_prefetched_uploads",
                )
            )

        data = {
            "podcasts": {
                "channel": [
                    serializers.get_channel_data(
                        channel, getattr(channel.library, "_prefetched_uploads", [])
                    )
                    for channel in channels
                ]
            },
        }
        return response.Response(data)

    @action(
        detail=False,
        methods=["get", "post"],
        url_name="get_newest_podcasts",
        url_path="getNewestPodcasts",
    )
    @requires_channels
    def get_newest_podcasts(self, request, *args, **kwargs):
        data = request.GET or request.POST
        try:
            count = int(data["count"])
        except (TypeError, KeyError, ValueError):
            count = 20
        channels = audio_models.Channel.objects.subscribed(request.user.actor)
        uploads = (
            music_models.Upload.objects.playable_by(request.user.actor)
            .filter(library__channel__in=channels)
            .select_related(
                "track__attachment_cover", "track__description", "library__channel"
            )
            .order_by("-track__creation_date")
        )
        data = {
            "newestPodcasts": {
                "episode": [
                    serializers.get_channel_episode_data(
                        upload, upload.library.channel.uuid
                    )
                    for upload in uploads[:count]
                ]
            }
        }
        return response.Response(data)

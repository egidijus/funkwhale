import datetime
import logging
import time
import uuid

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

import feedparser
import requests
import pytz

from rest_framework import serializers

from django.templatetags.static import static
from django.urls import reverse

from funkwhale_api.common import serializers as common_serializers
from funkwhale_api.common import utils as common_utils
from funkwhale_api.common import locales
from funkwhale_api.common import preferences
from funkwhale_api.common import session
from funkwhale_api.federation import actors
from funkwhale_api.federation import models as federation_models
from funkwhale_api.federation import serializers as federation_serializers
from funkwhale_api.federation import utils as federation_utils
from funkwhale_api.moderation import mrf
from funkwhale_api.music import models as music_models
from funkwhale_api.music import serializers as music_serializers
from funkwhale_api.tags import models as tags_models
from funkwhale_api.tags import serializers as tags_serializers
from funkwhale_api.users import serializers as users_serializers

from . import categories
from . import models


logger = logging.getLogger(__name__)


class ChannelMetadataSerializer(serializers.Serializer):
    itunes_category = serializers.ChoiceField(
        choices=categories.ITUNES_CATEGORIES, required=True
    )
    itunes_subcategory = serializers.CharField(required=False, allow_null=True)
    language = serializers.ChoiceField(required=True, choices=locales.ISO_639_CHOICES)
    copyright = serializers.CharField(required=False, allow_null=True, max_length=255)
    owner_name = serializers.CharField(required=False, allow_null=True, max_length=255)
    owner_email = serializers.EmailField(required=False, allow_null=True)
    explicit = serializers.BooleanField(required=False)

    def validate(self, validated_data):
        validated_data = super().validate(validated_data)
        subcategory = self._validate_itunes_subcategory(
            validated_data["itunes_category"], validated_data.get("itunes_subcategory")
        )
        if subcategory:
            validated_data["itunes_subcategory"] = subcategory
        return validated_data

    def _validate_itunes_subcategory(self, parent, child):
        if not child:
            return

        if child not in categories.ITUNES_CATEGORIES[parent]:
            raise serializers.ValidationError(
                '"{}" is not a valid subcategory for "{}"'.format(child, parent)
            )

        return child


class ChannelCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=music_models.MAX_LENGTHS["ARTIST_NAME"])
    username = serializers.CharField(
        max_length=music_models.MAX_LENGTHS["ARTIST_NAME"],
        validators=[users_serializers.ASCIIUsernameValidator()],
    )
    description = common_serializers.ContentSerializer(allow_null=True)
    tags = tags_serializers.TagsListField()
    content_category = serializers.ChoiceField(
        choices=music_models.ARTIST_CONTENT_CATEGORY_CHOICES
    )
    metadata = serializers.DictField(required=False)
    cover = music_serializers.COVER_WRITE_FIELD

    def validate(self, validated_data):
        existing_channels = self.context["actor"].owned_channels.count()
        if existing_channels >= preferences.get("audio__max_channels"):
            raise serializers.ValidationError(
                "You have reached the maximum amount of allowed channels"
            )
        validated_data = super().validate(validated_data)
        metadata = validated_data.pop("metadata", {})
        if validated_data["content_category"] == "podcast":
            metadata_serializer = ChannelMetadataSerializer(data=metadata)
            metadata_serializer.is_valid(raise_exception=True)
            metadata = metadata_serializer.validated_data
        validated_data["metadata"] = metadata
        return validated_data

    def validate_username(self, value):
        if value.lower() in [n.lower() for n in settings.ACCOUNT_USERNAME_BLACKLIST]:
            raise serializers.ValidationError("This username is already taken")

        matching = federation_models.Actor.objects.local().filter(
            preferred_username__iexact=value
        )
        if matching.exists():
            raise serializers.ValidationError("This username is already taken")
        return value

    @transaction.atomic
    def create(self, validated_data):
        from . import views

        cover = validated_data.pop("cover", None)
        description = validated_data.get("description")
        artist = music_models.Artist.objects.create(
            attributed_to=validated_data["attributed_to"],
            name=validated_data["name"],
            content_category=validated_data["content_category"],
            attachment_cover=cover,
        )
        common_utils.attach_content(artist, "description", description)

        if validated_data.get("tags", []):
            tags_models.set_tags(artist, *validated_data["tags"])

        channel = models.Channel(
            artist=artist,
            attributed_to=validated_data["attributed_to"],
            metadata=validated_data["metadata"],
        )
        channel.actor = models.generate_actor(
            validated_data["username"], name=validated_data["name"],
        )

        channel.library = music_models.Library.objects.create(
            name=channel.actor.preferred_username,
            privacy_level="everyone",
            actor=validated_data["attributed_to"],
        )
        channel.save()
        channel = views.ChannelViewSet.queryset.get(pk=channel.pk)
        return channel

    def to_representation(self, obj):
        return ChannelSerializer(obj, context=self.context).data


NOOP = object()


class ChannelUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=music_models.MAX_LENGTHS["ARTIST_NAME"])
    description = common_serializers.ContentSerializer(allow_null=True)
    tags = tags_serializers.TagsListField()
    content_category = serializers.ChoiceField(
        choices=music_models.ARTIST_CONTENT_CATEGORY_CHOICES
    )
    metadata = serializers.DictField(required=False)
    cover = music_serializers.COVER_WRITE_FIELD

    def validate(self, validated_data):
        validated_data = super().validate(validated_data)
        require_metadata_validation = False
        new_content_category = validated_data.get("content_category")
        metadata = validated_data.pop("metadata", NOOP)
        if (
            new_content_category == "podcast"
            and self.instance.artist.content_category != "postcast"
        ):
            # updating channel, setting as podcast
            require_metadata_validation = True
        elif self.instance.artist.content_category == "postcast" and metadata != NOOP:
            # channel is podcast, and metadata was updated
            require_metadata_validation = True
        else:
            metadata = self.instance.metadata

        if require_metadata_validation:
            metadata_serializer = ChannelMetadataSerializer(data=metadata)
            metadata_serializer.is_valid(raise_exception=True)
            metadata = metadata_serializer.validated_data

        validated_data["metadata"] = metadata
        return validated_data

    @transaction.atomic
    def update(self, obj, validated_data):
        if validated_data.get("tags") is not None:
            tags_models.set_tags(obj.artist, *validated_data["tags"])
        actor_update_fields = []
        artist_update_fields = []

        obj.metadata = validated_data["metadata"]
        obj.save(update_fields=["metadata"])

        if "description" in validated_data:
            common_utils.attach_content(
                obj.artist, "description", validated_data["description"]
            )

        if "name" in validated_data:
            actor_update_fields.append(("name", validated_data["name"]))
            artist_update_fields.append(("name", validated_data["name"]))

        if "content_category" in validated_data:
            artist_update_fields.append(
                ("content_category", validated_data["content_category"])
            )

        if "cover" in validated_data:
            artist_update_fields.append(("attachment_cover", validated_data["cover"]))

        if actor_update_fields:
            for field, value in actor_update_fields:
                setattr(obj.actor, field, value)
            obj.actor.save(update_fields=[f for f, _ in actor_update_fields])

        if artist_update_fields:
            for field, value in artist_update_fields:
                setattr(obj.artist, field, value)
            obj.artist.save(update_fields=[f for f, _ in artist_update_fields])

        return obj

    def to_representation(self, obj):
        return ChannelSerializer(obj, context=self.context).data


class ChannelSerializer(serializers.ModelSerializer):
    artist = serializers.SerializerMethodField()
    actor = serializers.SerializerMethodField()
    downloads_count = serializers.SerializerMethodField()
    attributed_to = federation_serializers.APIActorSerializer()
    rss_url = serializers.CharField(source="get_rss_url")
    url = serializers.SerializerMethodField()

    class Meta:
        model = models.Channel
        fields = [
            "uuid",
            "artist",
            "attributed_to",
            "actor",
            "creation_date",
            "metadata",
            "rss_url",
            "url",
            "downloads_count",
        ]

    def get_artist(self, obj):
        return music_serializers.serialize_artist_simple(obj.artist)

    def to_representation(self, obj):
        data = super().to_representation(obj)
        if self.context.get("subscriptions_count"):
            data["subscriptions_count"] = self.get_subscriptions_count(obj)
        return data

    def get_subscriptions_count(self, obj):
        return obj.actor.received_follows.exclude(approved=False).count()

    def get_downloads_count(self, obj):
        return getattr(obj, "_downloads_count", None)

    def get_actor(self, obj):
        if obj.attributed_to == actors.get_service_actor():
            return None
        return federation_serializers.APIActorSerializer(obj.actor).data

    def get_url(self, obj):
        return obj.actor.url


class SubscriptionSerializer(serializers.Serializer):
    approved = serializers.BooleanField(read_only=True)
    fid = serializers.URLField(read_only=True)
    uuid = serializers.UUIDField(read_only=True)
    creation_date = serializers.DateTimeField(read_only=True)

    def to_representation(self, obj):
        data = super().to_representation(obj)
        data["channel"] = ChannelSerializer(obj.target.channel).data
        return data


class RssSubscribeSerializer(serializers.Serializer):
    url = serializers.URLField()


class FeedFetchException(Exception):
    pass


class BlockedFeedException(FeedFetchException):
    pass


def retrieve_feed(url):
    try:
        logger.info("Fetching RSS feed at %s", url)
        response = session.get_session().get(url)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if e.response:
            raise FeedFetchException(
                "Error while fetching feed: HTTP {}".format(e.response.status_code)
            )
        raise FeedFetchException("Error while fetching feed: unknown error")
    except requests.exceptions.Timeout:
        raise FeedFetchException("Error while fetching feed: timeout")
    except requests.exceptions.ConnectionError:
        raise FeedFetchException("Error while fetching feed: connection error")
    except requests.RequestException as e:
        raise FeedFetchException("Error while fetching feed: {}".format(e))
    except Exception as e:
        raise FeedFetchException("Error while fetching feed: {}".format(e))

    return response


@transaction.atomic
def get_channel_from_rss_url(url, raise_exception=False):
    # first, check if the url is blocked
    is_valid, _ = mrf.inbox.apply({"id": url})
    if not is_valid:
        logger.warn("Feed fetch for url %s dropped by MRF", url)
        raise BlockedFeedException("This feed or domain is blocked")

    # retrieve the XML payload at the given URL
    response = retrieve_feed(url)

    parsed_feed = feedparser.parse(response.text)
    serializer = RssFeedSerializer(data=parsed_feed["feed"])
    if not serializer.is_valid(raise_exception=raise_exception):
        raise FeedFetchException("Invalid xml content: {}".format(serializer.errors))

    # second mrf check with validated data
    urls_to_check = set()
    atom_link = serializer.validated_data.get("atom_link")

    if atom_link and atom_link != url:
        urls_to_check.add(atom_link)

    if serializer.validated_data["link"] != url:
        urls_to_check.add(serializer.validated_data["link"])

    for u in urls_to_check:
        is_valid, _ = mrf.inbox.apply({"id": u})
        if not is_valid:
            logger.warn("Feed fetch for url %s dropped by MRF", u)
            raise BlockedFeedException("This feed or domain is blocked")

    # now, we're clear, we can save the data
    channel = serializer.save(rss_url=url)

    entries = parsed_feed.entries or []
    uploads = []
    track_defaults = {}
    existing_uploads = list(
        channel.library.uploads.all().select_related(
            "track__description", "track__attachment_cover"
        )
    )
    if parsed_feed.feed.get("rights"):
        track_defaults["copyright"] = parsed_feed.feed.rights[
            : music_models.MAX_LENGTHS["COPYRIGHT"]
        ]
    for entry in entries[: settings.PODCASTS_RSS_FEED_MAX_ITEMS]:
        logger.debug("Importing feed item %s", entry.id)
        s = RssFeedItemSerializer(data=entry)
        if not s.is_valid(raise_exception=raise_exception):
            logger.debug("Skipping invalid RSS feed item %s, ", entry, str(s.errors))
            continue
        uploads.append(
            s.save(channel, existing_uploads=existing_uploads, **track_defaults)
        )

    common_utils.on_commit(
        music_models.TrackActor.create_entries,
        library=channel.library,
        delete_existing=True,
    )
    if uploads:
        latest_track_date = max([upload.track.creation_date for upload in uploads])
        common_utils.update_modification_date(channel.artist, date=latest_track_date)
    return channel, uploads


# RSS related stuff
# https://github.com/simplepie/simplepie-ng/wiki/Spec:-iTunes-Podcast-RSS
# is extremely useful


class RssFeedSerializer(serializers.Serializer):
    title = serializers.CharField()
    link = serializers.URLField(required=False, allow_blank=True)
    language = serializers.CharField(required=False, allow_blank=True)
    rights = serializers.CharField(required=False, allow_blank=True)
    itunes_explicit = serializers.BooleanField(required=False, allow_null=True)
    tags = serializers.ListField(required=False)
    atom_link = serializers.DictField(required=False)
    links = serializers.ListField(required=False)
    summary_detail = serializers.DictField(required=False)
    author_detail = serializers.DictField(required=False)
    image = serializers.DictField(required=False)

    def validate_atom_link(self, v):
        if (
            v.get("rel", "self") == "self"
            and v.get("type", "application/rss+xml") == "application/rss+xml"
        ):
            return v["href"]

    def validate_links(self, v):
        for link in v:
            if link.get("rel") == "self":
                return link.get("href")

    def validate_summary_detail(self, v):
        content = v.get("value")
        if not content:
            return
        return {
            "content_type": v.get("type", "text/plain"),
            "text": content,
        }

    def validate_image(self, v):
        url = v.get("href")
        if url:
            return {
                "url": url,
                "mimetype": common_utils.get_mimetype_from_ext(url) or "image/jpeg",
            }

    def validate_tags(self, v):
        data = {}
        for row in v:
            if row.get("scheme") != "http://www.itunes.com/":
                continue
            term = row["term"]
            if "parent" not in data and term in categories.ITUNES_CATEGORIES:
                data["parent"] = term
            elif "child" not in data and term in categories.ITUNES_SUBCATEGORIES:
                data["child"] = term
            elif (
                term not in categories.ITUNES_SUBCATEGORIES
                and term not in categories.ITUNES_CATEGORIES
            ):
                raw_tags = term.split(" ")
                data["tags"] = []
                tag_serializer = tags_serializers.TagNameField()
                for tag in raw_tags:
                    try:
                        data["tags"].append(tag_serializer.to_internal_value(tag))
                    except Exception:
                        pass

        return data

    def validate(self, data):
        validated_data = super().validate(data)
        if not validated_data.get("link"):
            validated_data["link"] = validated_data.get("links")
        if not validated_data.get("link"):
            raise serializers.ValidationError("Missing link")
        return validated_data

    @transaction.atomic
    def save(self, rss_url):
        validated_data = self.validated_data
        # because there may be redirections from the original feed URL
        real_rss_url = validated_data.get("atom_link", rss_url) or rss_url
        service_actor = actors.get_service_actor()
        author = validated_data.get("author_detail", {})
        categories = validated_data.get("tags", {})
        metadata = {
            "explicit": validated_data.get("itunes_explicit", False),
            "copyright": validated_data.get("rights"),
            "owner_name": author.get("name"),
            "owner_email": author.get("email"),
            "itunes_category": categories.get("parent"),
            "itunes_subcategory": categories.get("child"),
            "language": validated_data.get("language"),
        }
        public_url = validated_data["link"]
        existing = (
            models.Channel.objects.external_rss()
            .filter(
                Q(rss_url=real_rss_url) | Q(rss_url=rss_url) | Q(actor__url=public_url)
            )
            .first()
        )
        channel_defaults = {
            "rss_url": real_rss_url,
            "metadata": metadata,
        }
        if existing:
            artist_kwargs = {"channel": existing}
            actor_kwargs = {"channel": existing}
            actor_defaults = {"url": public_url}
        else:
            artist_kwargs = {"pk": None}
            actor_kwargs = {"pk": None}
            preferred_username = "rssfeed-{}".format(uuid.uuid4())
            actor_defaults = {
                "preferred_username": preferred_username,
                "type": "Application",
                "domain": service_actor.domain,
                "url": public_url,
                "fid": federation_utils.full_url(
                    reverse(
                        "federation:actors-detail",
                        kwargs={"preferred_username": preferred_username},
                    )
                ),
            }
            channel_defaults["attributed_to"] = service_actor

        actor_defaults["last_fetch_date"] = timezone.now()

        # create/update the artist profile
        artist, created = music_models.Artist.objects.update_or_create(
            **artist_kwargs,
            defaults={
                "attributed_to": service_actor,
                "name": validated_data["title"][
                    : music_models.MAX_LENGTHS["ARTIST_NAME"]
                ],
                "content_category": "podcast",
            },
        )

        cover = validated_data.get("image")

        if cover:
            common_utils.attach_file(artist, "attachment_cover", cover)
        tags = categories.get("tags", [])

        if tags:
            tags_models.set_tags(artist, *tags)

        summary = validated_data.get("summary_detail")
        if summary:
            common_utils.attach_content(artist, "description", summary)

        if created:
            channel_defaults["artist"] = artist

        # create/update the actor
        actor, created = federation_models.Actor.objects.update_or_create(
            **actor_kwargs, defaults=actor_defaults
        )
        if created:
            channel_defaults["actor"] = actor

        # create the library
        if not existing:
            channel_defaults["library"] = music_models.Library.objects.create(
                actor=service_actor,
                privacy_level=settings.PODCASTS_THIRD_PARTY_VISIBILITY,
                name=actor_defaults["preferred_username"],
            )

        # create/update the channel
        channel, created = models.Channel.objects.update_or_create(
            pk=existing.pk if existing else None, defaults=channel_defaults,
        )
        return channel


class ItunesDurationField(serializers.CharField):
    def to_internal_value(self, v):
        try:
            return int(v)
        except (ValueError, TypeError):
            pass
        parts = v.split(":")
        int_parts = []
        for part in parts:
            try:
                int_parts.append(int(part))
            except (ValueError, TypeError):
                raise serializers.ValidationError("Invalid duration {}".format(v))

        if len(int_parts) == 2:
            hours = 0
            minutes, seconds = int_parts
        elif len(int_parts) == 3:
            hours, minutes, seconds = int_parts
        else:
            raise serializers.ValidationError("Invalid duration {}".format(v))

        return (hours * 3600) + (minutes * 60) + seconds


class DummyField(serializers.Field):
    def to_internal_value(self, v):
        return v


def get_cached_upload(uploads, expected_track_uuid):
    for upload in uploads:
        if upload.track.uuid == expected_track_uuid:
            return upload


class PermissiveIntegerField(serializers.IntegerField):
    def to_internal_value(self, v):
        try:
            return super().to_internal_value(v)
        except serializers.ValidationError:
            return self.default


class RssFeedItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    rights = serializers.CharField(required=False, allow_blank=True)
    itunes_season = serializers.IntegerField(
        required=False, allow_null=True, default=None
    )
    itunes_episode = PermissiveIntegerField(
        required=False, allow_null=True, default=None
    )
    itunes_duration = ItunesDurationField(
        required=False, allow_null=True, default=None, allow_blank=True
    )
    links = serializers.ListField()
    tags = serializers.ListField(required=False)
    summary_detail = serializers.DictField(required=False)
    published_parsed = DummyField(required=False)
    image = serializers.DictField(required=False)

    def validate_summary_detail(self, v):
        content = v.get("value")
        if not content:
            return
        return {
            "content_type": v.get("type", "text/plain"),
            "text": content,
        }

    def validate_image(self, v):
        url = v.get("href")
        if url:
            return {
                "url": url,
                "mimetype": common_utils.get_mimetype_from_ext(url) or "image/jpeg",
            }

    def validate_links(self, v):
        data = {}
        for row in v:
            if not row.get("type", "").startswith("audio/"):
                continue
            if row.get("rel") != "enclosure":
                continue
            try:
                size = int(row.get("length", 0) or 0) or None
            except (TypeError, ValueError):
                raise serializers.ValidationError("Invalid size")

            data["audio"] = {
                "mimetype": common_utils.get_audio_mimetype(row["type"]),
                "size": size,
                "source": row["href"],
            }

        if not data:
            raise serializers.ValidationError("No valid audio enclosure found")

        return data

    def validate_tags(self, v):
        data = {}
        for row in v:
            if row.get("scheme") != "http://www.itunes.com/":
                continue
            term = row["term"]
            raw_tags = term.split(" ")
            data["tags"] = []
            tag_serializer = tags_serializers.TagNameField()
            for tag in raw_tags:
                try:
                    data["tags"].append(tag_serializer.to_internal_value(tag))
                except Exception:
                    pass

        return data

    @transaction.atomic
    def save(self, channel, existing_uploads=[], **track_defaults):
        validated_data = self.validated_data
        categories = validated_data.get("tags", {})
        expected_uuid = uuid.uuid3(
            uuid.NAMESPACE_URL, "rss://{}-{}".format(channel.pk, validated_data["id"])
        )
        existing_upload = get_cached_upload(existing_uploads, expected_uuid)
        if existing_upload:
            existing_track = existing_upload.track
        else:
            existing_track = (
                music_models.Track.objects.filter(
                    uuid=expected_uuid, artist__channel=channel
                )
                .select_related("description", "attachment_cover")
                .first()
            )
            if existing_track:
                existing_upload = existing_track.uploads.filter(
                    library=channel.library
                ).first()

        track_defaults = track_defaults
        track_defaults.update(
            {
                "disc_number": validated_data.get("itunes_season", 1) or 1,
                "position": validated_data.get("itunes_episode", 1) or 1,
                "title": validated_data["title"][
                    : music_models.MAX_LENGTHS["TRACK_TITLE"]
                ],
                "artist": channel.artist,
            }
        )
        if "rights" in validated_data:
            track_defaults["copyright"] = validated_data["rights"][
                : music_models.MAX_LENGTHS["COPYRIGHT"]
            ]

        if "published_parsed" in validated_data:
            track_defaults["creation_date"] = datetime.datetime.fromtimestamp(
                time.mktime(validated_data["published_parsed"])
            ).replace(tzinfo=pytz.utc)

        upload_defaults = {
            "source": validated_data["links"]["audio"]["source"],
            "size": validated_data["links"]["audio"]["size"],
            "mimetype": validated_data["links"]["audio"]["mimetype"],
            "duration": validated_data.get("itunes_duration") or None,
            "import_status": "finished",
            "library": channel.library,
        }
        if existing_track:
            track_kwargs = {"pk": existing_track.pk}
            upload_kwargs = {"track": existing_track}
        else:
            track_kwargs = {"pk": None}
            track_defaults["uuid"] = expected_uuid
            upload_kwargs = {"pk": None}

        if existing_upload and existing_upload.source != upload_defaults["source"]:
            # delete existing upload, the url to the audio file has changed
            existing_upload.delete()

        # create/update the track
        track, created = music_models.Track.objects.update_or_create(
            **track_kwargs, defaults=track_defaults,
        )
        # optimisation for reducing SQL queries, because we cannot use select_related with
        # update or create, so we restore the cache by hand
        if existing_track:
            for field in ["attachment_cover", "description"]:
                cached_id_value = getattr(existing_track, "{}_id".format(field))
                new_id_value = getattr(track, "{}_id".format(field))
                if new_id_value and cached_id_value == new_id_value:
                    setattr(track, field, getattr(existing_track, field))

        cover = validated_data.get("image")

        if cover:
            common_utils.attach_file(track, "attachment_cover", cover)
        tags = categories.get("tags", [])

        if tags:
            tags_models.set_tags(track, *tags)

        summary = validated_data.get("summary_detail")
        if summary:
            common_utils.attach_content(track, "description", summary)

        if created:
            upload_defaults["track"] = track

        # create/update the upload
        upload, created = music_models.Upload.objects.update_or_create(
            **upload_kwargs, defaults=upload_defaults
        )

        return upload


def rfc822_date(dt):
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def rss_duration(seconds):
    if not seconds:
        return "00:00:00"
    full_hours = seconds // 3600
    full_minutes = (seconds - (full_hours * 3600)) // 60
    remaining_seconds = seconds - (full_hours * 3600) - (full_minutes * 60)
    return "{}:{}:{}".format(
        str(full_hours).zfill(2),
        str(full_minutes).zfill(2),
        str(remaining_seconds).zfill(2),
    )


def rss_serialize_item(upload):
    data = {
        "title": [{"value": upload.track.title}],
        "itunes:title": [{"value": upload.track.title}],
        "guid": [{"cdata_value": str(upload.uuid), "isPermalink": "false"}],
        "pubDate": [{"value": rfc822_date(upload.creation_date)}],
        "itunes:duration": [{"value": rss_duration(upload.duration)}],
        "itunes:explicit": [{"value": "no"}],
        "itunes:episodeType": [{"value": "full"}],
        "itunes:season": [{"value": upload.track.disc_number or 1}],
        "itunes:episode": [{"value": upload.track.position or 1}],
        "link": [{"value": federation_utils.full_url(upload.track.get_absolute_url())}],
        "enclosure": [
            {
                # we enforce MP3, since it's the only format supported everywhere
                "url": federation_utils.full_url(upload.get_listen_url(to="mp3")),
                "length": upload.size or 0,
                "type": "audio/mpeg",
            }
        ],
    }
    if upload.track.description:
        data["itunes:subtitle"] = [{"value": upload.track.description.truncate(255)}]
        data["itunes:summary"] = [{"cdata_value": upload.track.description.rendered}]
        data["description"] = [{"value": upload.track.description.as_plain_text}]

    if upload.track.attachment_cover:
        data["itunes:image"] = [
            {"href": upload.track.attachment_cover.download_url_original}
        ]

    tagged_items = getattr(upload.track, "_prefetched_tagged_items", [])
    if tagged_items:
        data["itunes:keywords"] = [
            {"value": " ".join([ti.tag.name for ti in tagged_items])}
        ]

    return data


def rss_serialize_channel(channel):
    metadata = channel.metadata or {}
    explicit = metadata.get("explicit", False)
    copyright = metadata.get("copyright", "All rights reserved")
    owner_name = metadata.get("owner_name", channel.attributed_to.display_name)
    owner_email = metadata.get("owner_email")
    itunes_category = metadata.get("itunes_category")
    itunes_subcategory = metadata.get("itunes_subcategory")
    language = metadata.get("language")

    data = {
        "title": [{"value": channel.artist.name}],
        "copyright": [{"value": copyright}],
        "itunes:explicit": [{"value": "no" if not explicit else "yes"}],
        "itunes:author": [{"value": owner_name}],
        "itunes:owner": [{"itunes:name": [{"value": owner_name}]}],
        "itunes:type": [{"value": "episodic"}],
        "link": [{"value": channel.get_absolute_url()}],
        "atom:link": [
            {
                "href": channel.get_rss_url(),
                "rel": "self",
                "type": "application/rss+xml",
            },
            {
                "href": channel.actor.fid,
                "rel": "alternate",
                "type": "application/activity+json",
            },
        ],
    }
    if language:
        data["language"] = [{"value": language}]

    if owner_email:
        data["itunes:owner"][0]["itunes:email"] = [{"value": owner_email}]

    if itunes_category:
        node = {"text": itunes_category}
        if itunes_subcategory:
            node["itunes:category"] = [{"text": itunes_subcategory}]
        data["itunes:category"] = [node]

    if channel.artist.description:
        data["itunes:subtitle"] = [{"value": channel.artist.description.truncate(255)}]
        data["itunes:summary"] = [{"cdata_value": channel.artist.description.rendered}]
        data["description"] = [{"value": channel.artist.description.as_plain_text}]

    if channel.artist.attachment_cover:
        data["itunes:image"] = [
            {"href": channel.artist.attachment_cover.download_url_original}
        ]
    else:
        placeholder_url = federation_utils.full_url(
            static("images/podcasts-cover-placeholder.png")
        )
        data["itunes:image"] = [{"href": placeholder_url}]

    tagged_items = getattr(channel.artist, "_prefetched_tagged_items", [])

    if tagged_items:
        data["itunes:keywords"] = [
            {"value": " ".join([ti.tag.name for ti in tagged_items])}
        ]

    return data


def rss_serialize_channel_full(channel, uploads):
    channel_data = rss_serialize_channel(channel)
    channel_data["item"] = [rss_serialize_item(upload) for upload in uploads]
    return {"channel": channel_data}


# OPML stuff
def get_opml_outline(channel):
    return {
        "title": channel.artist.name,
        "text": channel.artist.name,
        "type": "rss",
        "xmlUrl": channel.get_rss_url(),
        "htmlUrl": channel.actor.url,
    }


def get_opml(channels, date, title):
    return {
        "version": "2.0",
        "head": [{"date": [{"value": rfc822_date(date)}], "title": [{"value": title}]}],
        "body": [{"outline": [get_opml_outline(channel) for channel in channels]}],
    }

import logging
import os
import urllib.parse
import uuid

from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from rest_framework import serializers

from funkwhale_api.common import utils as common_utils
from funkwhale_api.common import models as common_models
from funkwhale_api.moderation import models as moderation_models
from funkwhale_api.moderation import serializers as moderation_serializers
from funkwhale_api.moderation import signals as moderation_signals
from funkwhale_api.music import licenses
from funkwhale_api.music import models as music_models
from funkwhale_api.music import tasks as music_tasks
from funkwhale_api.tags import models as tags_models

from . import activity, actors, contexts, jsonld, models, utils

logger = logging.getLogger(__name__)


def include_if_not_none(data, value, field):
    if value is not None:
        data[field] = value


class MultipleSerializer(serializers.Serializer):
    """
    A serializer that will try multiple serializers in turn
    """

    def __init__(self, *args, **kwargs):
        self.allowed = kwargs.pop("allowed")
        super().__init__(*args, **kwargs)

    def to_internal_value(self, v):
        last_exception = None
        for serializer_class in self.allowed:
            s = serializer_class(data=v)
            try:
                s.is_valid(raise_exception=True)
            except serializers.ValidationError as e:
                last_exception = e
            else:
                return s.validated_data

        raise last_exception


class TruncatedCharField(serializers.CharField):
    def __init__(self, *args, **kwargs):
        self.truncate_length = kwargs.pop("truncate_length")
        super().__init__(*args, **kwargs)

    def to_internal_value(self, v):
        v = super().to_internal_value(v)
        if v:
            v = v[: self.truncate_length]
        return v


class TagSerializer(jsonld.JsonLdSerializer):
    type = serializers.ChoiceField(choices=[contexts.AS.Hashtag])
    name = serializers.CharField(max_length=100)

    class Meta:
        jsonld_mapping = {"name": jsonld.first_val(contexts.AS.name)}

    def validate_name(self, value):
        if value.startswith("#"):
            # remove trailing #
            value = value[1:]
        return value


def tag_list(tagged_items):
    return [
        repr_tag(item.tag.name)
        for item in sorted(set(tagged_items.all()), key=lambda i: i.tag.name)
    ]


def is_mimetype(mt, allowed_mimetypes):
    for allowed in allowed_mimetypes:
        if allowed.endswith("/*"):
            if mt.startswith(allowed.replace("*", "")):
                return True
        else:
            if mt == allowed:
                return True
    return False


class MediaSerializer(jsonld.JsonLdSerializer):
    mediaType = serializers.CharField()

    def __init__(self, *args, **kwargs):
        self.allowed_mimetypes = kwargs.pop("allowed_mimetypes", [])
        self.allow_empty_mimetype = kwargs.pop("allow_empty_mimetype", False)
        super().__init__(*args, **kwargs)
        self.fields["mediaType"].required = not self.allow_empty_mimetype
        self.fields["mediaType"].allow_null = self.allow_empty_mimetype

    def validate_mediaType(self, v):
        if not self.allowed_mimetypes:
            # no restrictions
            return v
        if self.allow_empty_mimetype and not v:
            return None

        if not is_mimetype(v, self.allowed_mimetypes):
            raise serializers.ValidationError(
                "Invalid mimetype {}. Allowed: {}".format(v, self.allowed_mimetypes)
            )
        return v


class LinkSerializer(MediaSerializer):
    type = serializers.ChoiceField(choices=[contexts.AS.Link])
    href = serializers.URLField(max_length=500)
    bitrate = serializers.IntegerField(min_value=0, required=False)
    size = serializers.IntegerField(min_value=0, required=False)

    class Meta:
        jsonld_mapping = {
            "href": jsonld.first_id(contexts.AS.href),
            "mediaType": jsonld.first_val(contexts.AS.mediaType),
            "bitrate": jsonld.first_val(contexts.FW.bitrate),
            "size": jsonld.first_val(contexts.FW.size),
        }


class LinkListSerializer(serializers.ListField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("child", LinkSerializer(jsonld_expand=False))
        self.keep_mediatype = kwargs.pop("keep_mediatype", [])
        super().__init__(*args, **kwargs)

    def to_internal_value(self, v):
        links = super().to_internal_value(v)
        if not self.keep_mediatype:
            # no further filtering required
            return links
        links = [
            link
            for link in links
            if link.get("mediaType")
            and is_mimetype(link["mediaType"], self.keep_mediatype)
        ]
        if not self.allow_empty and len(links) == 0:
            self.fail("empty")

        return links


class ImageSerializer(MediaSerializer):
    type = serializers.ChoiceField(choices=[contexts.AS.Image, contexts.AS.Link])
    href = serializers.URLField(max_length=500, required=False)
    url = serializers.URLField(max_length=500, required=False)

    class Meta:
        jsonld_mapping = {
            "url": jsonld.first_id(contexts.AS.url),
            "href": jsonld.first_id(contexts.AS.href),
            "mediaType": jsonld.first_val(contexts.AS.mediaType),
        }

    def validate(self, data):
        validated_data = super().validate(data)
        if "url" not in validated_data:
            try:
                validated_data["url"] = validated_data["href"]
            except KeyError:
                if self.required:
                    raise serializers.ValidationError(
                        "You need to provide a url or href"
                    )

        return validated_data


class URLSerializer(jsonld.JsonLdSerializer):
    href = serializers.URLField(max_length=500)
    mediaType = serializers.CharField(required=False)

    class Meta:
        jsonld_mapping = {
            "href": jsonld.first_id(contexts.AS.href, aliases=[jsonld.raw("@id")]),
            "mediaType": jsonld.first_val(contexts.AS.mediaType),
        }


class EndpointsSerializer(jsonld.JsonLdSerializer):
    sharedInbox = serializers.URLField(max_length=500, required=False)

    class Meta:
        jsonld_mapping = {"sharedInbox": jsonld.first_id(contexts.AS.sharedInbox)}


class PublicKeySerializer(jsonld.JsonLdSerializer):
    publicKeyPem = serializers.CharField(trim_whitespace=False)

    class Meta:
        jsonld_mapping = {"publicKeyPem": jsonld.first_val(contexts.SEC.publicKeyPem)}


def get_by_media_type(urls, media_type):
    for url in urls:
        if url.get("mediaType", "text/html") == media_type:
            return url


class BasicActorSerializer(jsonld.JsonLdSerializer):
    id = serializers.URLField(max_length=500)
    type = serializers.ChoiceField(
        choices=[getattr(contexts.AS, c[0]) for c in models.TYPE_CHOICES]
    )

    class Meta:
        jsonld_mapping = {}


class ActorSerializer(jsonld.JsonLdSerializer):
    id = serializers.URLField(max_length=500)
    outbox = serializers.URLField(max_length=500, required=False)
    inbox = serializers.URLField(max_length=500, required=False)
    url = serializers.ListField(
        child=URLSerializer(jsonld_expand=False), required=False, min_length=0
    )
    type = serializers.ChoiceField(
        choices=[getattr(contexts.AS, c[0]) for c in models.TYPE_CHOICES]
    )
    preferredUsername = serializers.CharField()
    manuallyApprovesFollowers = serializers.NullBooleanField(required=False)
    name = serializers.CharField(
        required=False, max_length=200, allow_blank=True, allow_null=True
    )
    summary = TruncatedCharField(
        truncate_length=common_models.CONTENT_TEXT_MAX_LENGTH,
        required=False,
        allow_null=True,
    )
    followers = serializers.URLField(max_length=500, required=False)
    following = serializers.URLField(max_length=500, required=False, allow_null=True)
    publicKey = PublicKeySerializer(required=False)
    endpoints = EndpointsSerializer(required=False)
    icon = ImageSerializer(
        allowed_mimetypes=["image/*"],
        allow_null=True,
        required=False,
        allow_empty_mimetype=True,
    )
    attributedTo = serializers.URLField(max_length=500, required=False)

    tags = serializers.ListField(
        child=TagSerializer(), min_length=0, required=False, allow_null=True
    )

    category = serializers.CharField(required=False)
    # languages = serializers.Char(
    #     music_models.ARTIST_CONTENT_CATEGORY_CHOICES, required=False, default="music",
    # )

    class Meta:
        # not strictly necessary because it's not a model serializer
        # but used by tasks.py/fetch
        model = models.Actor

        jsonld_mapping = {
            "outbox": jsonld.first_id(contexts.AS.outbox),
            "inbox": jsonld.first_id(contexts.LDP.inbox),
            "following": jsonld.first_id(contexts.AS.following),
            "followers": jsonld.first_id(contexts.AS.followers),
            "preferredUsername": jsonld.first_val(contexts.AS.preferredUsername),
            "summary": jsonld.first_val(contexts.AS.summary),
            "name": jsonld.first_val(contexts.AS.name),
            "publicKey": jsonld.first_obj(contexts.SEC.publicKey),
            "manuallyApprovesFollowers": jsonld.first_val(
                contexts.AS.manuallyApprovesFollowers
            ),
            "mediaType": jsonld.first_val(contexts.AS.mediaType),
            "endpoints": jsonld.first_obj(contexts.AS.endpoints),
            "icon": jsonld.first_obj(contexts.AS.icon),
            "url": jsonld.raw(contexts.AS.url),
            "attributedTo": jsonld.first_id(contexts.AS.attributedTo),
            "tags": jsonld.raw(contexts.AS.tag),
            "category": jsonld.first_val(contexts.SC.category),
            # "language": jsonld.first_val(contexts.SC.inLanguage),
        }

    def validate_category(self, v):
        return (
            v
            if v in [t for t, _ in music_models.ARTIST_CONTENT_CATEGORY_CHOICES]
            else None
        )

    def to_representation(self, instance):
        ret = {
            "id": instance.fid,
            "outbox": instance.outbox_url,
            "inbox": instance.inbox_url,
            "preferredUsername": instance.preferred_username,
            "type": instance.type,
        }
        if instance.name:
            ret["name"] = instance.name
        if instance.followers_url:
            ret["followers"] = instance.followers_url
        if instance.following_url:
            ret["following"] = instance.following_url
        if instance.manually_approves_followers is not None:
            ret["manuallyApprovesFollowers"] = instance.manually_approves_followers

        if instance.summary_obj_id:
            ret["summary"] = instance.summary_obj.rendered
        urls = []
        if instance.url:
            urls.append(
                {"type": "Link", "href": instance.url, "mediaType": "text/html"}
            )

        channel = instance.get_channel()
        if channel:
            ret["url"] = [
                {
                    "type": "Link",
                    "href": instance.channel.get_absolute_url()
                    if instance.channel.artist.is_local
                    else instance.get_absolute_url(),
                    "mediaType": "text/html",
                },
                {
                    "type": "Link",
                    "href": instance.channel.get_rss_url(),
                    "mediaType": "application/rss+xml",
                },
            ]
            include_image(ret, channel.artist.attachment_cover, "icon")
            if channel.artist.description_id:
                ret["summary"] = channel.artist.description.rendered
            ret["attributedTo"] = channel.attributed_to.fid
            ret["category"] = channel.artist.content_category
            ret["tag"] = tag_list(channel.artist.tagged_items.all())
        else:
            ret["url"] = [
                {
                    "type": "Link",
                    "href": instance.get_absolute_url(),
                    "mediaType": "text/html",
                }
            ]
            include_image(ret, instance.attachment_icon, "icon")

        ret["@context"] = jsonld.get_default_context()
        if instance.public_key:
            ret["publicKey"] = {
                "owner": instance.fid,
                "publicKeyPem": instance.public_key,
                "id": "{}#main-key".format(instance.fid),
            }
        ret["endpoints"] = {}

        if instance.shared_inbox_url:
            ret["endpoints"]["sharedInbox"] = instance.shared_inbox_url
        return ret

    def prepare_missing_fields(self):
        kwargs = {
            "fid": self.validated_data["id"],
            "outbox_url": self.validated_data.get("outbox"),
            "inbox_url": self.validated_data.get("inbox"),
            "following_url": self.validated_data.get("following"),
            "followers_url": self.validated_data.get("followers"),
            "type": self.validated_data["type"],
            "name": self.validated_data.get("name"),
            "preferred_username": self.validated_data["preferredUsername"],
        }
        url = get_by_media_type(self.validated_data.get("url", []), "text/html")
        if url:
            kwargs["url"] = url["href"]

        maf = self.validated_data.get("manuallyApprovesFollowers")
        if maf is not None:
            kwargs["manually_approves_followers"] = maf
        domain = urllib.parse.urlparse(kwargs["fid"]).netloc
        domain, domain_created = models.Domain.objects.get_or_create(pk=domain)
        if domain_created and not domain.is_local:
            from . import tasks

            # first time we see the domain, we trigger nodeinfo fetching
            tasks.update_domain_nodeinfo(domain_name=domain.name)

        kwargs["domain"] = domain
        for endpoint, url in self.validated_data.get("endpoints", {}).items():
            if endpoint == "sharedInbox":
                kwargs["shared_inbox_url"] = url
                break
        try:
            kwargs["public_key"] = self.validated_data["publicKey"]["publicKeyPem"]
        except KeyError:
            pass
        return kwargs

    def validate_type(self, v):
        return v.split("#")[-1]

    def build(self):
        d = self.prepare_missing_fields()
        return models.Actor(**d)

    def save(self, **kwargs):
        d = self.prepare_missing_fields()
        d.update(kwargs)
        actor = models.Actor.objects.update_or_create(fid=d["fid"], defaults=d)[0]
        common_utils.attach_content(
            actor, "summary_obj", self.validated_data["summary"]
        )
        if "icon" in self.validated_data:
            new_value = self.validated_data["icon"]
            common_utils.attach_file(
                actor,
                "attachment_icon",
                {"url": new_value["url"], "mimetype": new_value.get("mediaType")}
                if new_value
                else None,
            )

        rss_url = get_by_media_type(
            self.validated_data.get("url", []), "application/rss+xml"
        )
        if rss_url:
            rss_url = rss_url["href"]
        attributed_to = self.validated_data.get("attributedTo", actor.fid)
        if rss_url:
            # if the actor is attributed to another actor, and there is a RSS url,
            # then we consider it's a channel
            create_or_update_channel(
                actor,
                rss_url=rss_url,
                attributed_to_fid=attributed_to,
                **self.validated_data
            )
        return actor

    def validate(self, data):
        validated_data = super().validate(data)
        if "summary" in data:
            validated_data["summary"] = {
                "content_type": "text/html",
                "text": data["summary"],
            }
        else:
            validated_data["summary"] = None
        return validated_data


def create_or_update_channel(actor, rss_url, attributed_to_fid, **validated_data):
    from funkwhale_api.audio import models as audio_models

    attributed_to = actors.get_actor(attributed_to_fid)
    artist_defaults = {
        "name": validated_data.get("name", validated_data["preferredUsername"]),
        "fid": validated_data["id"],
        "content_category": validated_data.get("category", "music") or "music",
        "attributed_to": attributed_to,
    }
    artist, created = music_models.Artist.objects.update_or_create(
        channel__attributed_to=attributed_to,
        channel__actor=actor,
        defaults=artist_defaults,
    )
    common_utils.attach_content(artist, "description", validated_data.get("summary"))
    if "icon" in validated_data:
        new_value = validated_data["icon"]
        common_utils.attach_file(
            artist,
            "attachment_cover",
            {"url": new_value["url"], "mimetype": new_value.get("mediaType")}
            if new_value
            else None,
        )
    tags = [t["name"] for t in validated_data.get("tags", []) or []]
    tags_models.set_tags(artist, *tags)
    if created:
        uid = uuid.uuid4()
        fid = utils.full_url(
            reverse("federation:music:libraries-detail", kwargs={"uuid": uid})
        )
        library = attributed_to.libraries.create(
            privacy_level="everyone", name=artist_defaults["name"], fid=fid, uuid=uid,
        )
    else:
        library = artist.channel.library
    channel_defaults = {
        "actor": actor,
        "attributed_to": attributed_to,
        "rss_url": rss_url,
        "artist": artist,
        "library": library,
    }
    channel, created = audio_models.Channel.objects.update_or_create(
        actor=actor, attributed_to=attributed_to, defaults=channel_defaults,
    )
    return channel


class APIActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Actor
        fields = [
            "fid",
            "url",
            "creation_date",
            "summary",
            "preferred_username",
            "name",
            "last_fetch_date",
            "domain",
            "type",
            "manually_approves_followers",
            "full_username",
            "is_local",
        ]


class BaseActivitySerializer(serializers.Serializer):
    id = serializers.URLField(max_length=500, required=False)
    type = serializers.CharField(max_length=100)
    actor = serializers.URLField(max_length=500)
    object = serializers.JSONField(required=False, allow_null=True)

    def validate_actor(self, v):
        expected = self.context.get("actor")
        if expected and expected.fid != v:
            raise serializers.ValidationError("Invalid actor")
        if expected:
            # avoid a DB lookup
            return expected
        try:
            return models.Actor.objects.get(fid=v)
        except models.Actor.DoesNotExist:
            raise serializers.ValidationError("Actor not found")

    def create(self, validated_data):
        return models.Activity.objects.create(
            fid=validated_data.get("id"),
            actor=validated_data["actor"],
            payload=self.initial_data,
            type=validated_data["type"],
        )

    def validate(self, data):
        self.validate_recipients(data, self.initial_data)
        return super().validate(data)

    def validate_recipients(self, data, payload):
        """
        Ensure we have at least a to/cc field with valid actors
        """
        data["to"] = payload.get("to", [])
        data["cc"] = payload.get("cc", [])

        if (
            not data["to"]
            and data.get("type") in ["Follow", "Accept"]
            and data.get("object")
        ):
            # there isn't always a to field for Accept/Follow
            # in their follow activity, so we consider the recipient
            # to be the follow object
            if data["type"] == "Follow":
                data["to"].append(str(data.get("object")))
            else:
                data["to"].append(data.get("object", {}).get("actor"))

        if not data["to"] and not data["cc"] and not self.context.get("recipients"):
            raise serializers.ValidationError(
                "We cannot handle an activity with no recipient"
            )


class FollowSerializer(serializers.Serializer):
    id = serializers.URLField(max_length=500)
    object = serializers.URLField(max_length=500)
    actor = serializers.URLField(max_length=500)
    type = serializers.ChoiceField(choices=["Follow"])

    def validate_object(self, v):
        expected = self.context.get("follow_target")
        if self.parent:
            # it's probably an accept, so everything is inverted, the actor
            # the recipient does not matter
            recipient = None
        else:
            recipient = self.context.get("recipient")
        if expected and expected.fid != v:
            raise serializers.ValidationError("Invalid target")
        try:
            obj = models.Actor.objects.get(fid=v)
            if recipient and recipient.fid != obj.fid:
                raise serializers.ValidationError("Invalid target")
            return obj
        except models.Actor.DoesNotExist:
            pass
        try:
            qs = music_models.Library.objects.filter(fid=v)
            if recipient:
                qs = qs.filter(actor=recipient)
            return qs.get()
        except music_models.Library.DoesNotExist:
            pass

        raise serializers.ValidationError("Target not found")

    def validate_actor(self, v):
        expected = self.context.get("follow_actor")
        if expected and expected.fid != v:
            raise serializers.ValidationError("Invalid actor")
        try:
            return models.Actor.objects.get(fid=v)
        except models.Actor.DoesNotExist:
            raise serializers.ValidationError("Actor not found")

    def save(self, **kwargs):
        target = self.validated_data["object"]

        if target._meta.label == "music.Library":
            follow_class = models.LibraryFollow
        else:
            follow_class = models.Follow
        defaults = kwargs
        defaults["fid"] = self.validated_data["id"]
        approved = kwargs.pop("approved", None)
        follow, created = follow_class.objects.update_or_create(
            actor=self.validated_data["actor"],
            target=self.validated_data["object"],
            defaults=defaults,
        )
        if not created:
            # We likely received a new follow when we had an existing one in database
            # this can happen when two instances are out of sync, e.g because some
            # messages are not delivered properly. In this case, we don't change
            # the follow approved status and return the follow as is.
            # We set a new UUID to ensure the follow urls are updated properly
            # cf #830
            follow.uuid = uuid.uuid4()
            follow.save(update_fields=["uuid"])
            return follow

        # it's a brand new follow, we use the approved value stored earlier
        if approved != follow.approved:
            follow.approved = approved
            follow.save(update_fields=["approved"])

        return follow

    def to_representation(self, instance):
        return {
            "@context": jsonld.get_default_context(),
            "actor": instance.actor.fid,
            "id": instance.get_federation_id(),
            "object": instance.target.fid,
            "type": "Follow",
        }


class APIFollowSerializer(serializers.ModelSerializer):
    actor = APIActorSerializer()
    target = APIActorSerializer()

    class Meta:
        model = models.Follow
        fields = [
            "uuid",
            "id",
            "approved",
            "creation_date",
            "modification_date",
            "actor",
            "target",
        ]


class AcceptFollowSerializer(serializers.Serializer):
    id = serializers.URLField(max_length=500, required=False)
    actor = serializers.URLField(max_length=500)
    object = FollowSerializer()
    type = serializers.ChoiceField(choices=["Accept"])

    def validate_actor(self, v):
        expected = self.context.get("actor")
        if expected and expected.fid != v:
            raise serializers.ValidationError("Invalid actor")
        try:
            return models.Actor.objects.get(fid=v)
        except models.Actor.DoesNotExist:
            raise serializers.ValidationError("Actor not found")

    def validate(self, validated_data):
        # we ensure the accept actor actually match the follow target / library owner
        target = validated_data["object"]["object"]

        if target._meta.label == "music.Library":
            expected = target.actor
            follow_class = models.LibraryFollow
        else:
            expected = target
            follow_class = models.Follow
        if validated_data["actor"] != expected:
            raise serializers.ValidationError("Actor mismatch")
        try:
            validated_data["follow"] = (
                follow_class.objects.filter(
                    target=target, actor=validated_data["object"]["actor"]
                )
                .exclude(approved=True)
                .select_related()
                .get()
            )
        except follow_class.DoesNotExist:
            raise serializers.ValidationError("No follow to accept")
        return validated_data

    def to_representation(self, instance):
        if instance.target._meta.label == "music.Library":
            actor = instance.target.actor
        else:
            actor = instance.target

        return {
            "@context": jsonld.get_default_context(),
            "id": instance.get_federation_id() + "/accept",
            "type": "Accept",
            "actor": actor.fid,
            "object": FollowSerializer(instance).data,
        }

    def save(self):
        follow = self.validated_data["follow"]
        follow.approved = True
        follow.save()
        if follow.target._meta.label == "music.Library":
            follow.target.schedule_scan(actor=follow.actor)
        return follow


class UndoFollowSerializer(serializers.Serializer):
    id = serializers.URLField(max_length=500)
    actor = serializers.URLField(max_length=500)
    object = FollowSerializer()
    type = serializers.ChoiceField(choices=["Undo"])

    def validate_actor(self, v):
        expected = self.context.get("actor")

        if expected and expected.fid != v:
            raise serializers.ValidationError("Invalid actor")
        try:
            return models.Actor.objects.get(fid=v)
        except models.Actor.DoesNotExist:
            raise serializers.ValidationError("Actor not found")

    def validate(self, validated_data):
        # we ensure the accept actor actually match the follow actor
        if validated_data["actor"] != validated_data["object"]["actor"]:
            raise serializers.ValidationError("Actor mismatch")

        target = validated_data["object"]["object"]

        if target._meta.label == "music.Library":
            follow_class = models.LibraryFollow
        else:
            follow_class = models.Follow

        try:
            validated_data["follow"] = follow_class.objects.filter(
                actor=validated_data["actor"], target=target
            ).get()
        except follow_class.DoesNotExist:
            raise serializers.ValidationError("No follow to remove")
        return validated_data

    def to_representation(self, instance):
        return {
            "@context": jsonld.get_default_context(),
            "id": instance.get_federation_id() + "/undo",
            "type": "Undo",
            "actor": instance.actor.fid,
            "object": FollowSerializer(instance).data,
        }

    def save(self):
        return self.validated_data["follow"].delete()


class ActorWebfingerSerializer(serializers.Serializer):
    subject = serializers.CharField()
    aliases = serializers.ListField(child=serializers.URLField(max_length=500))
    links = serializers.ListField()
    actor_url = serializers.URLField(max_length=500, required=False)

    def validate(self, validated_data):
        validated_data["actor_url"] = None
        for l in validated_data["links"]:
            try:
                if not l["rel"] == "self":
                    continue
                if not l["type"] == "application/activity+json":
                    continue
                validated_data["actor_url"] = l["href"]
                break
            except KeyError:
                pass
        if validated_data["actor_url"] is None:
            raise serializers.ValidationError("No valid actor url found")
        return validated_data

    def to_representation(self, instance):
        data = {}
        data["subject"] = "acct:{}".format(instance.webfinger_subject)
        data["links"] = [
            {"rel": "self", "href": instance.fid, "type": "application/activity+json"}
        ]
        data["aliases"] = [instance.fid]
        return data


class ActivitySerializer(serializers.Serializer):
    actor = serializers.URLField(max_length=500)
    id = serializers.URLField(max_length=500, required=False)
    type = serializers.ChoiceField(choices=[(c, c) for c in activity.ACTIVITY_TYPES])
    object = serializers.JSONField(required=False)
    target = serializers.JSONField(required=False)

    def validate_object(self, value):
        try:
            type = value["type"]
        except KeyError:
            raise serializers.ValidationError("Missing object type")
        except TypeError:
            # probably a URL
            return value
        try:
            object_serializer = OBJECT_SERIALIZERS[type]
        except KeyError:
            raise serializers.ValidationError("Unsupported type {}".format(type))

        serializer = object_serializer(data=value)
        serializer.is_valid(raise_exception=True)
        return serializer.data

    def validate_actor(self, value):
        request_actor = self.context.get("actor")
        if request_actor and request_actor.fid != value:
            raise serializers.ValidationError(
                "The actor making the request do not match" " the activity actor"
            )
        return value

    def to_representation(self, conf):
        d = {}
        d.update(conf)

        if self.context.get("include_ap_context", True):
            d["@context"] = jsonld.get_default_context()
        return d


class ObjectSerializer(serializers.Serializer):
    id = serializers.URLField(max_length=500)
    url = serializers.URLField(max_length=500, required=False, allow_null=True)
    type = serializers.ChoiceField(choices=[(c, c) for c in activity.OBJECT_TYPES])
    content = serializers.CharField(required=False, allow_null=True)
    summary = serializers.CharField(required=False, allow_null=True)
    name = serializers.CharField(required=False, allow_null=True)
    published = serializers.DateTimeField(required=False, allow_null=True)
    updated = serializers.DateTimeField(required=False, allow_null=True)
    to = serializers.ListField(
        child=serializers.URLField(max_length=500), required=False, allow_null=True
    )
    cc = serializers.ListField(
        child=serializers.URLField(max_length=500), required=False, allow_null=True
    )
    bto = serializers.ListField(
        child=serializers.URLField(max_length=500), required=False, allow_null=True
    )
    bcc = serializers.ListField(
        child=serializers.URLField(max_length=500), required=False, allow_null=True
    )


OBJECT_SERIALIZERS = {t: ObjectSerializer for t in activity.OBJECT_TYPES}


def get_additional_fields(data):
    UNSET = object()
    additional_fields = {}
    for field in ["name", "summary"]:
        v = data.get(field, UNSET)
        if v == UNSET:
            continue
        additional_fields[field] = v

    return additional_fields


PAGINATED_COLLECTION_JSONLD_MAPPING = {
    "totalItems": jsonld.first_val(contexts.AS.totalItems),
    "first": jsonld.first_id(contexts.AS.first),
    "last": jsonld.first_id(contexts.AS.last),
    "partOf": jsonld.first_id(contexts.AS.partOf),
}


class PaginatedCollectionSerializer(jsonld.JsonLdSerializer):
    type = serializers.ChoiceField(
        choices=[contexts.AS.Collection, contexts.AS.OrderedCollection]
    )
    totalItems = serializers.IntegerField(min_value=0)
    id = serializers.URLField(max_length=500)
    first = serializers.URLField(max_length=500)
    last = serializers.URLField(max_length=500)

    class Meta:
        jsonld_mapping = PAGINATED_COLLECTION_JSONLD_MAPPING

    def to_representation(self, conf):
        paginator = Paginator(conf["items"], conf.get("page_size", 20))
        first = common_utils.set_query_parameter(conf["id"], page=1)
        current = first
        last = common_utils.set_query_parameter(conf["id"], page=paginator.num_pages)
        d = {
            "id": conf["id"],
            # XXX Stable release: remove the obsolete actor field
            "actor": conf["actor"].fid,
            "attributedTo": conf["actor"].fid,
            "totalItems": paginator.count,
            "type": conf.get("type", "Collection"),
            "current": current,
            "first": first,
            "last": last,
        }
        d.update(get_additional_fields(conf))
        if self.context.get("include_ap_context", True):
            d["@context"] = jsonld.get_default_context()
        return d


class LibrarySerializer(PaginatedCollectionSerializer):
    type = serializers.ChoiceField(
        choices=[contexts.AS.Collection, contexts.FW.Library]
    )
    actor = serializers.URLField(max_length=500, required=False)
    attributedTo = serializers.URLField(max_length=500, required=False)
    name = serializers.CharField()
    summary = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    followers = serializers.URLField(max_length=500)
    audience = serializers.ChoiceField(
        choices=["", "./", None, "https://www.w3.org/ns/activitystreams#Public"],
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    class Meta:
        # not strictly necessary because it's not a model serializer
        # but used by tasks.py/fetch
        model = music_models.Library

        jsonld_mapping = common_utils.concat_dicts(
            PAGINATED_COLLECTION_JSONLD_MAPPING,
            {
                "name": jsonld.first_val(contexts.AS.name),
                "summary": jsonld.first_val(contexts.AS.summary),
                "audience": jsonld.first_id(contexts.AS.audience),
                "followers": jsonld.first_id(contexts.AS.followers),
                "actor": jsonld.first_id(contexts.AS.actor),
                "attributedTo": jsonld.first_id(contexts.AS.attributedTo),
            },
        )

    def validate(self, validated_data):
        d = super().validate(validated_data)
        actor = d.get("actor")
        attributed_to = d.get("attributedTo")
        if not actor and not attributed_to:
            raise serializers.ValidationError(
                "You need to provide at least actor or attributedTo"
            )

        d["attributedTo"] = attributed_to or actor
        return d

    def to_representation(self, library):
        conf = {
            "id": library.fid,
            "name": library.name,
            "summary": library.description,
            "page_size": 100,
            # XXX Stable release: remove the obsolete actor field
            "actor": library.actor,
            "attributedTo": library.actor,
            "items": library.uploads.for_federation(),
            "type": "Library",
        }
        r = super().to_representation(conf)
        r["audience"] = (
            contexts.AS.Public if library.privacy_level == "everyone" else ""
        )
        r["followers"] = library.followers_url
        return r

    def create(self, validated_data):
        if self.instance:
            actor = self.instance.actor
        else:
            actor = utils.retrieve_ap_object(
                validated_data["attributedTo"],
                actor=self.context.get("fetch_actor"),
                queryset=models.Actor,
                serializer_class=ActorSerializer,
            )
        privacy = {"": "me", "./": "me", None: "me", contexts.AS.Public: "everyone"}
        library, created = music_models.Library.objects.update_or_create(
            fid=validated_data["id"],
            actor=actor,
            defaults={
                "uploads_count": validated_data["totalItems"],
                "name": validated_data["name"],
                "description": validated_data.get("summary"),
                "followers_url": validated_data["followers"],
                "privacy_level": privacy[validated_data["audience"]],
            },
        )
        return library

    def update(self, instance, validated_data):
        return self.create(validated_data)


class CollectionPageSerializer(jsonld.JsonLdSerializer):
    type = serializers.ChoiceField(choices=[contexts.AS.CollectionPage])
    totalItems = serializers.IntegerField(min_value=0)
    items = serializers.ListField()
    actor = serializers.URLField(max_length=500, required=False)
    attributedTo = serializers.URLField(max_length=500, required=False)
    id = serializers.URLField(max_length=500)
    first = serializers.URLField(max_length=500)
    last = serializers.URLField(max_length=500)
    next = serializers.URLField(max_length=500, required=False)
    prev = serializers.URLField(max_length=500, required=False)
    partOf = serializers.URLField(max_length=500)

    class Meta:
        jsonld_mapping = {
            "totalItems": jsonld.first_val(contexts.AS.totalItems),
            "items": jsonld.raw(contexts.AS.items),
            "actor": jsonld.first_id(contexts.AS.actor),
            "attributedTo": jsonld.first_id(contexts.AS.attributedTo),
            "first": jsonld.first_id(contexts.AS.first),
            "last": jsonld.first_id(contexts.AS.last),
            "next": jsonld.first_id(contexts.AS.next),
            "prev": jsonld.first_id(contexts.AS.prev),
            "partOf": jsonld.first_id(contexts.AS.partOf),
        }

    def validate_items(self, v):
        item_serializer = self.context.get("item_serializer")
        if not item_serializer:
            return v
        raw_items = [item_serializer(data=i, context=self.context) for i in v]
        valid_items = []
        for i in raw_items:
            try:
                i.is_valid(raise_exception=True)
                valid_items.append(i)
            except serializers.ValidationError:
                logger.debug("Invalid item %s: %s", i.data, i.errors)

        return valid_items

    def to_representation(self, conf):
        page = conf["page"]
        first = common_utils.set_query_parameter(conf["id"], page=1)
        last = common_utils.set_query_parameter(
            conf["id"], page=page.paginator.num_pages
        )
        id = common_utils.set_query_parameter(conf["id"], page=page.number)
        d = {
            "id": id,
            "partOf": conf["id"],
            "totalItems": page.paginator.count,
            "type": "CollectionPage",
            "first": first,
            "last": last,
            "items": [
                conf["item_serializer"](
                    i, context={"actor": conf["actor"], "include_ap_context": False}
                ).data
                for i in page.object_list
            ],
        }
        if conf["actor"]:
            # XXX Stable release: remove the obsolete actor field
            d["actor"] = conf["actor"].fid
            d["attributedTo"] = conf["actor"].fid

        if page.has_previous():
            d["prev"] = common_utils.set_query_parameter(
                conf["id"], page=page.previous_page_number()
            )

        if page.has_next():
            d["next"] = common_utils.set_query_parameter(
                conf["id"], page=page.next_page_number()
            )
        d.update(get_additional_fields(conf))
        if self.context.get("include_ap_context", True):
            d["@context"] = jsonld.get_default_context()
        return d


MUSIC_ENTITY_JSONLD_MAPPING = {
    "name": jsonld.first_val(contexts.AS.name),
    "published": jsonld.first_val(contexts.AS.published),
    "musicbrainzId": jsonld.first_val(contexts.FW.musicbrainzId),
    "attributedTo": jsonld.first_id(contexts.AS.attributedTo),
    "tags": jsonld.raw(contexts.AS.tag),
    "mediaType": jsonld.first_val(contexts.AS.mediaType),
    "content": jsonld.first_val(contexts.AS.content),
}


def repr_tag(tag_name):
    return {"type": "Hashtag", "name": "#{}".format(tag_name)}


def include_content(repr, content_obj):
    if not content_obj:
        return

    repr["content"] = common_utils.render_html(
        content_obj.text, content_obj.content_type
    )
    repr["mediaType"] = "text/html"


def include_image(repr, attachment, field="image"):
    if attachment:
        repr[field] = {
            "type": "Image",
            "url": attachment.download_url_original,
            "mediaType": attachment.mimetype or "image/jpeg",
        }
    else:
        repr[field] = None


class MusicEntitySerializer(jsonld.JsonLdSerializer):
    id = serializers.URLField(max_length=500)
    published = serializers.DateTimeField()
    musicbrainzId = serializers.UUIDField(allow_null=True, required=False)
    name = serializers.CharField(max_length=1000)
    attributedTo = serializers.URLField(max_length=500, allow_null=True, required=False)
    updateable_fields = []
    tags = serializers.ListField(
        child=TagSerializer(), min_length=0, required=False, allow_null=True
    )
    mediaType = serializers.ChoiceField(
        choices=common_models.CONTENT_TEXT_SUPPORTED_TYPES,
        default="text/html",
        required=False,
    )
    content = TruncatedCharField(
        truncate_length=common_models.CONTENT_TEXT_MAX_LENGTH,
        required=False,
        allow_null=True,
    )

    def update(self, instance, validated_data):
        return self.update_or_create(validated_data)

    @transaction.atomic
    def update_or_create(self, validated_data):
        instance = self.instance or self.Meta.model(fid=validated_data["id"])
        creating = instance.pk is None
        attributed_to_fid = validated_data.get("attributedTo")
        if attributed_to_fid:
            validated_data["attributedTo"] = actors.get_actor(attributed_to_fid)
        updated_fields = common_utils.get_updated_fields(
            self.updateable_fields, validated_data, instance
        )
        updated_fields = self.validate_updated_data(instance, updated_fields)
        if creating:
            instance, created = self.Meta.model.objects.get_or_create(
                fid=validated_data["id"], defaults=updated_fields
            )
        else:
            music_tasks.update_library_entity(instance, updated_fields)

        tags = [t["name"] for t in validated_data.get("tags", []) or []]
        tags_models.set_tags(instance, *tags)
        common_utils.attach_content(
            instance, "description", validated_data.get("description")
        )
        return instance

    def get_tags_repr(self, instance):
        return tag_list(instance.tagged_items.all())

    def validate_updated_data(self, instance, validated_data):
        try:
            attachment_cover = validated_data.pop("attachment_cover")
        except KeyError:
            return validated_data

        if (
            instance.attachment_cover
            and instance.attachment_cover.url == attachment_cover["url"]
        ):
            # we already have the proper attachment
            return validated_data
        # create the attachment by hand so it can be attached as the cover
        validated_data["attachment_cover"] = common_models.Attachment.objects.create(
            mimetype=attachment_cover.get("mediaType"),
            url=attachment_cover["url"],
            actor=instance.attributed_to,
        )
        return validated_data

    def validate(self, data):
        validated_data = super().validate(data)
        if data.get("content"):
            validated_data["description"] = {
                "content_type": data["mediaType"],
                "text": data["content"],
            }
        return validated_data


class ArtistSerializer(MusicEntitySerializer):
    image = ImageSerializer(
        allowed_mimetypes=["image/*"],
        allow_null=True,
        required=False,
        allow_empty_mimetype=True,
    )
    updateable_fields = [
        ("name", "name"),
        ("musicbrainzId", "mbid"),
        ("attributedTo", "attributed_to"),
        ("image", "attachment_cover"),
    ]

    class Meta:
        model = music_models.Artist
        jsonld_mapping = common_utils.concat_dicts(
            MUSIC_ENTITY_JSONLD_MAPPING,
            {
                "released": jsonld.first_val(contexts.FW.released),
                "artists": jsonld.first_attr(contexts.FW.artists, "@list"),
                "image": jsonld.first_obj(contexts.AS.image),
            },
        )

    def to_representation(self, instance):
        d = {
            "type": "Artist",
            "id": instance.fid,
            "name": instance.name,
            "published": instance.creation_date.isoformat(),
            "musicbrainzId": str(instance.mbid) if instance.mbid else None,
            "attributedTo": instance.attributed_to.fid
            if instance.attributed_to
            else None,
            "tag": self.get_tags_repr(instance),
        }
        include_content(d, instance.description)
        include_image(d, instance.attachment_cover)
        if self.context.get("include_ap_context", self.parent is None):
            d["@context"] = jsonld.get_default_context()
        return d

    create = MusicEntitySerializer.update_or_create


class AlbumSerializer(MusicEntitySerializer):
    released = serializers.DateField(allow_null=True, required=False)
    artists = serializers.ListField(
        child=MultipleSerializer(allowed=[BasicActorSerializer, ArtistSerializer]),
        min_length=1,
    )
    # XXX: 1.0 rename to image
    cover = ImageSerializer(
        allowed_mimetypes=["image/*"],
        allow_null=True,
        required=False,
        allow_empty_mimetype=True,
    )
    updateable_fields = [
        ("name", "title"),
        ("cover", "attachment_cover"),
        ("musicbrainzId", "mbid"),
        ("attributedTo", "attributed_to"),
        ("released", "release_date"),
        ("_artist", "artist"),
    ]

    class Meta:
        model = music_models.Album
        jsonld_mapping = common_utils.concat_dicts(
            MUSIC_ENTITY_JSONLD_MAPPING,
            {
                "released": jsonld.first_val(contexts.FW.released),
                "artists": jsonld.first_attr(contexts.FW.artists, "@list"),
                "cover": jsonld.first_obj(contexts.FW.cover),
            },
        )

    def to_representation(self, instance):
        d = {
            "type": "Album",
            "id": instance.fid,
            "name": instance.title,
            "published": instance.creation_date.isoformat(),
            "musicbrainzId": str(instance.mbid) if instance.mbid else None,
            "released": instance.release_date.isoformat()
            if instance.release_date
            else None,
            "attributedTo": instance.attributed_to.fid
            if instance.attributed_to
            else None,
            "tag": self.get_tags_repr(instance),
        }
        if instance.artist.get_channel():
            d["artists"] = [
                {
                    "type": instance.artist.channel.actor.type,
                    "id": instance.artist.channel.actor.fid,
                }
            ]
        else:
            d["artists"] = [
                ArtistSerializer(
                    instance.artist, context={"include_ap_context": False}
                ).data
            ]
        include_content(d, instance.description)
        if instance.attachment_cover:
            d["cover"] = {
                "type": "Link",
                "href": instance.attachment_cover.download_url_original,
                "mediaType": instance.attachment_cover.mimetype or "image/jpeg",
            }
            include_image(d, instance.attachment_cover)

        if self.context.get("include_ap_context", self.parent is None):
            d["@context"] = jsonld.get_default_context()
        return d

    def validate(self, data):
        validated_data = super().validate(data)
        if not self.parent:
            artist_data = validated_data["artists"][0]
            if artist_data.get("type", "Artist") == "Artist":
                validated_data["_artist"] = utils.retrieve_ap_object(
                    artist_data["id"],
                    actor=self.context.get("fetch_actor"),
                    queryset=music_models.Artist,
                    serializer_class=ArtistSerializer,
                )
            else:
                # we have an actor as an artist, so it's a channel
                actor = actors.get_actor(artist_data["id"])
                validated_data["_artist"] = actor.channel.artist

        return validated_data

    create = MusicEntitySerializer.update_or_create


class TrackSerializer(MusicEntitySerializer):
    position = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    disc = serializers.IntegerField(min_value=1, allow_null=True, required=False)
    artists = serializers.ListField(child=ArtistSerializer(), min_length=1)
    album = AlbumSerializer()
    license = serializers.URLField(allow_null=True, required=False)
    copyright = serializers.CharField(allow_null=True, required=False)
    image = ImageSerializer(
        allowed_mimetypes=["image/*"],
        allow_null=True,
        required=False,
        allow_empty_mimetype=True,
    )

    updateable_fields = [
        ("name", "title"),
        ("musicbrainzId", "mbid"),
        ("attributedTo", "attributed_to"),
        ("disc", "disc_number"),
        ("position", "position"),
        ("copyright", "copyright"),
        ("license", "license"),
        ("image", "attachment_cover"),
    ]

    class Meta:
        model = music_models.Track
        jsonld_mapping = common_utils.concat_dicts(
            MUSIC_ENTITY_JSONLD_MAPPING,
            {
                "album": jsonld.first_obj(contexts.FW.album),
                "artists": jsonld.first_attr(contexts.FW.artists, "@list"),
                "copyright": jsonld.first_val(contexts.FW.copyright),
                "disc": jsonld.first_val(contexts.FW.disc),
                "license": jsonld.first_id(contexts.FW.license),
                "position": jsonld.first_val(contexts.FW.position),
                "image": jsonld.first_obj(contexts.AS.image),
            },
        )

    def to_representation(self, instance):
        d = {
            "type": "Track",
            "id": instance.fid,
            "name": instance.title,
            "published": instance.creation_date.isoformat(),
            "musicbrainzId": str(instance.mbid) if instance.mbid else None,
            "position": instance.position,
            "disc": instance.disc_number,
            "license": instance.local_license["identifiers"][0]
            if instance.local_license
            else None,
            "copyright": instance.copyright if instance.copyright else None,
            "artists": [
                ArtistSerializer(
                    instance.artist, context={"include_ap_context": False}
                ).data
            ],
            "album": AlbumSerializer(
                instance.album, context={"include_ap_context": False}
            ).data,
            "attributedTo": instance.attributed_to.fid
            if instance.attributed_to
            else None,
            "tag": self.get_tags_repr(instance),
        }
        include_content(d, instance.description)
        include_image(d, instance.attachment_cover)
        if self.context.get("include_ap_context", self.parent is None):
            d["@context"] = jsonld.get_default_context()
        return d

    def create(self, validated_data):
        from funkwhale_api.music import tasks as music_tasks

        references = {}
        actors_to_fetch = set()
        actors_to_fetch.add(
            common_utils.recursive_getattr(
                validated_data, "attributedTo", permissive=True
            )
        )
        actors_to_fetch.add(
            common_utils.recursive_getattr(
                validated_data, "album.attributedTo", permissive=True
            )
        )
        artists = (
            common_utils.recursive_getattr(validated_data, "artists", permissive=True)
            or []
        )
        album_artists = (
            common_utils.recursive_getattr(
                validated_data, "album.artists", permissive=True
            )
            or []
        )
        for artist in artists + album_artists:
            actors_to_fetch.add(artist.get("attributedTo"))

        for url in actors_to_fetch:
            if not url:
                continue
            references[url] = actors.get_actor(url)
        metadata = music_tasks.federation_audio_track_to_metadata(
            validated_data, references
        )

        from_activity = self.context.get("activity")
        if from_activity:
            metadata["from_activity_id"] = from_activity.pk
        track = music_tasks.get_track_from_import_metadata(metadata, update_cover=True)

        return track

    def update(self, obj, validated_data):
        if validated_data.get("license"):
            validated_data["license"] = licenses.match(validated_data["license"])
        return super().update(obj, validated_data)


class UploadSerializer(jsonld.JsonLdSerializer):
    type = serializers.ChoiceField(choices=[contexts.AS.Audio])
    id = serializers.URLField(max_length=500)
    library = serializers.URLField(max_length=500)
    url = LinkSerializer(allowed_mimetypes=["audio/*"])
    published = serializers.DateTimeField()
    updated = serializers.DateTimeField(required=False, allow_null=True)
    bitrate = serializers.IntegerField(min_value=0)
    size = serializers.IntegerField(min_value=0)
    duration = serializers.IntegerField(min_value=0)

    track = TrackSerializer(required=True)

    class Meta:
        model = music_models.Upload
        jsonld_mapping = {
            "track": jsonld.first_obj(contexts.FW.track),
            "library": jsonld.first_id(contexts.FW.library),
            "url": jsonld.first_obj(contexts.AS.url),
            "published": jsonld.first_val(contexts.AS.published),
            "updated": jsonld.first_val(contexts.AS.updated),
            "duration": jsonld.first_val(contexts.AS.duration),
            "bitrate": jsonld.first_val(contexts.FW.bitrate),
            "size": jsonld.first_val(contexts.FW.size),
        }

    def validate_url(self, v):
        try:
            v["href"]
        except (KeyError, TypeError):
            raise serializers.ValidationError("Missing href")

        try:
            media_type = v["mediaType"]
        except (KeyError, TypeError):
            raise serializers.ValidationError("Missing mediaType")

        if not media_type or not media_type.startswith("audio/"):
            raise serializers.ValidationError("Invalid mediaType")

        return v

    def validate_library(self, v):
        lb = self.context.get("library")
        if lb:
            if lb.fid != v:
                raise serializers.ValidationError("Invalid library")
            return lb

        actor = self.context.get("actor")

        try:
            library = utils.retrieve_ap_object(
                v,
                actor=self.context.get("fetch_actor"),
                queryset=music_models.Library,
                serializer_class=LibrarySerializer,
            )
        except Exception:
            raise serializers.ValidationError("Invalid library")
        if actor and library.actor != actor:
            raise serializers.ValidationError("Invalid library")
        return library

    def update(self, instance, validated_data):
        return self.create(validated_data)

    @transaction.atomic
    def create(self, validated_data):
        instance = self.instance or None
        if not self.instance:
            try:
                instance = music_models.Upload.objects.get(fid=validated_data["id"])
            except music_models.Upload.DoesNotExist:
                pass

        if instance:
            data = {
                "mimetype": validated_data["url"]["mediaType"],
                "source": validated_data["url"]["href"],
                "creation_date": validated_data["published"],
                "modification_date": validated_data.get("updated"),
                "duration": validated_data["duration"],
                "size": validated_data["size"],
                "bitrate": validated_data["bitrate"],
                "import_status": "finished",
            }
            return music_models.Upload.objects.update_or_create(
                fid=validated_data["id"], defaults=data
            )[0]
        else:
            track = TrackSerializer(
                context={"activity": self.context.get("activity")}
            ).create(validated_data["track"])

            data = {
                "fid": validated_data["id"],
                "mimetype": validated_data["url"]["mediaType"],
                "source": validated_data["url"]["href"],
                "creation_date": validated_data["published"],
                "modification_date": validated_data.get("updated"),
                "track": track,
                "duration": validated_data["duration"],
                "size": validated_data["size"],
                "bitrate": validated_data["bitrate"],
                "library": validated_data["library"],
                "from_activity": self.context.get("activity"),
                "import_status": "finished",
            }
            return music_models.Upload.objects.create(**data)

    def to_representation(self, instance):
        track = instance.track
        d = {
            "type": "Audio",
            "id": instance.get_federation_id(),
            "library": instance.library.fid,
            "name": track.full_name,
            "published": instance.creation_date.isoformat(),
            "bitrate": instance.bitrate,
            "size": instance.size,
            "duration": instance.duration,
            "url": [
                {
                    "href": utils.full_url(instance.listen_url_no_download),
                    "type": "Link",
                    "mediaType": instance.mimetype,
                },
                {
                    "type": "Link",
                    "mediaType": "text/html",
                    "href": utils.full_url(instance.track.get_absolute_url()),
                },
            ],
            "track": TrackSerializer(track, context={"include_ap_context": False}).data,
            "to": contexts.AS.Public
            if instance.library.privacy_level == "everyone"
            else "",
            "attributedTo": instance.library.actor.fid,
        }
        if instance.modification_date:
            d["updated"] = instance.modification_date.isoformat()

        if self.context.get("include_ap_context", self.parent is None):
            d["@context"] = jsonld.get_default_context()
        return d


class ActorDeleteSerializer(jsonld.JsonLdSerializer):
    fid = serializers.URLField(max_length=500)

    class Meta:
        jsonld_mapping = {"fid": jsonld.first_id(contexts.AS.object)}


class FlagSerializer(jsonld.JsonLdSerializer):
    type = serializers.ChoiceField(choices=[contexts.AS.Flag])
    id = serializers.URLField(max_length=500)
    object = serializers.URLField(max_length=500)
    content = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    actor = serializers.URLField(max_length=500)
    type = serializers.ListField(
        child=TagSerializer(), min_length=0, required=False, allow_null=True
    )

    class Meta:
        jsonld_mapping = {
            "object": jsonld.first_id(contexts.AS.object),
            "content": jsonld.first_val(contexts.AS.content),
            "actor": jsonld.first_id(contexts.AS.actor),
            "type": jsonld.raw(contexts.AS.tag),
        }

    def validate_object(self, v):
        try:
            return utils.get_object_by_fid(v, local=True)
        except ObjectDoesNotExist:
            raise serializers.ValidationError(
                "Unknown id {} for reported object".format(v)
            )

    def validate_type(self, tags):
        if tags:
            for tag in tags:
                if tag["name"] in dict(moderation_models.REPORT_TYPES):
                    return tag["name"]
        return "other"

    def validate_actor(self, v):
        try:
            return models.Actor.objects.get(fid=v, domain=self.context["actor"].domain)
        except models.Actor.DoesNotExist:
            raise serializers.ValidationError("Invalid actor")

    def validate(self, data):
        validated_data = super().validate(data)

        return validated_data

    def create(self, validated_data):
        kwargs = {
            "target": validated_data["object"],
            "target_owner": moderation_serializers.get_target_owner(
                validated_data["object"]
            ),
            "target_state": moderation_serializers.get_target_state(
                validated_data["object"]
            ),
            "type": validated_data.get("type", "other"),
            "summary": validated_data.get("content"),
            "submitter": validated_data["actor"],
        }

        report, created = moderation_models.Report.objects.update_or_create(
            fid=validated_data["id"], defaults=kwargs,
        )
        moderation_signals.report_created.send(sender=None, report=report)
        return report

    def to_representation(self, instance):
        d = {
            "type": "Flag",
            "id": instance.get_federation_id(),
            "actor": actors.get_service_actor().fid,
            "object": [instance.target.fid],
            "content": instance.summary,
            "tag": [repr_tag(instance.type)],
        }

        if self.context.get("include_ap_context", self.parent is None):
            d["@context"] = jsonld.get_default_context()
        return d


class NodeInfoLinkSerializer(serializers.Serializer):
    href = serializers.URLField()
    rel = serializers.URLField()


class NodeInfoSerializer(serializers.Serializer):
    links = serializers.ListField(child=NodeInfoLinkSerializer(), min_length=1)


class ChannelOutboxSerializer(PaginatedCollectionSerializer):
    type = serializers.ChoiceField(choices=[contexts.AS.OrderedCollection])

    class Meta:
        jsonld_mapping = PAGINATED_COLLECTION_JSONLD_MAPPING

    def to_representation(self, channel):
        conf = {
            "id": channel.actor.outbox_url,
            "page_size": 100,
            "attributedTo": channel.actor,
            "actor": channel.actor,
            "items": channel.library.uploads.for_federation()
            .order_by("-creation_date")
            .filter(track__artist=channel.artist),
            "type": "OrderedCollection",
        }
        r = super().to_representation(conf)
        return r


class ChannelUploadSerializer(jsonld.JsonLdSerializer):
    id = serializers.URLField(max_length=500)
    type = serializers.ChoiceField(choices=[contexts.AS.Audio])
    url = LinkListSerializer(keep_mediatype=["audio/*"], min_length=1)
    name = TruncatedCharField(truncate_length=music_models.MAX_LENGTHS["TRACK_TITLE"])
    published = serializers.DateTimeField(required=False)
    duration = serializers.IntegerField(min_value=0, required=False)
    position = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    disc = serializers.IntegerField(min_value=1, allow_null=True, required=False)
    album = serializers.URLField(max_length=500, required=False)
    license = serializers.URLField(allow_null=True, required=False)
    attributedTo = serializers.URLField(max_length=500, required=False)
    copyright = TruncatedCharField(
        truncate_length=music_models.MAX_LENGTHS["COPYRIGHT"],
        allow_null=True,
        required=False,
    )
    image = ImageSerializer(
        allowed_mimetypes=["image/*"],
        allow_null=True,
        required=False,
        allow_empty_mimetype=True,
    )

    mediaType = serializers.ChoiceField(
        choices=common_models.CONTENT_TEXT_SUPPORTED_TYPES,
        default="text/html",
        required=False,
    )
    content = TruncatedCharField(
        truncate_length=common_models.CONTENT_TEXT_MAX_LENGTH,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    tags = serializers.ListField(
        child=TagSerializer(), min_length=0, required=False, allow_null=True
    )

    class Meta:
        jsonld_mapping = {
            "name": jsonld.first_val(contexts.AS.name),
            "url": jsonld.raw(contexts.AS.url),
            "published": jsonld.first_val(contexts.AS.published),
            "mediaType": jsonld.first_val(contexts.AS.mediaType),
            "content": jsonld.first_val(contexts.AS.content),
            "duration": jsonld.first_val(contexts.AS.duration),
            "album": jsonld.first_id(contexts.FW.album),
            "copyright": jsonld.first_val(contexts.FW.copyright),
            "disc": jsonld.first_val(contexts.FW.disc),
            "license": jsonld.first_id(contexts.FW.license),
            "position": jsonld.first_val(contexts.FW.position),
            "image": jsonld.first_obj(contexts.AS.image),
            "tags": jsonld.raw(contexts.AS.tag),
            "attributedTo": jsonld.first_id(contexts.AS.attributedTo),
        }

    def _validate_album(self, v):
        return utils.retrieve_ap_object(
            v,
            actor=actors.get_service_actor(),
            serializer_class=AlbumSerializer,
            queryset=music_models.Album.objects.filter(
                artist__channel=self.context["channel"]
            ),
        )

    def validate(self, data):
        if not self.context.get("channel"):
            if not data.get("attributedTo"):
                raise serializers.ValidationError(
                    "Missing channel context and no attributedTo available"
                )
            actor = actors.get_actor(data["attributedTo"])
            if not actor.get_channel():
                raise serializers.ValidationError("Not a channel")
            self.context["channel"] = actor.get_channel()
        if data.get("album"):
            data["album"] = self._validate_album(data["album"])
        validated_data = super().validate(data)
        if data.get("content"):
            validated_data["description"] = {
                "content_type": data["mediaType"],
                "text": data["content"],
            }
        return validated_data

    def to_representation(self, upload):
        data = {
            "id": upload.fid,
            "type": "Audio",
            "name": upload.track.title,
            "attributedTo": upload.library.channel.actor.fid,
            "published": upload.creation_date.isoformat(),
            "to": contexts.AS.Public
            if upload.library.privacy_level == "everyone"
            else "",
            "url": [
                {
                    "type": "Link",
                    "mediaType": "text/html",
                    "href": utils.full_url(upload.track.get_absolute_url()),
                },
                {
                    "type": "Link",
                    "mediaType": upload.mimetype,
                    "href": utils.full_url(upload.listen_url_no_download),
                },
            ],
        }
        if upload.track.album:
            data["album"] = upload.track.album.fid
        if upload.track.local_license:
            data["license"] = upload.track.local_license["identifiers"][0]

        include_if_not_none(data, upload.duration, "duration")
        include_if_not_none(data, upload.track.position, "position")
        include_if_not_none(data, upload.track.disc_number, "disc")
        include_if_not_none(data, upload.track.copyright, "copyright")
        include_if_not_none(data["url"][1], upload.bitrate, "bitrate")
        include_if_not_none(data["url"][1], upload.size, "size")
        include_content(data, upload.track.description)
        include_image(data, upload.track.attachment_cover)
        tags = [item.tag.name for item in upload.get_all_tagged_items()]
        if tags:
            data["tag"] = [repr_tag(name) for name in sorted(set(tags))]
            data["summary"] = " ".join(["#{}".format(name) for name in tags])

        if self.context.get("include_ap_context", True):
            data["@context"] = jsonld.get_default_context()

        return data

    def update(self, instance, validated_data):
        return self.update_or_create(validated_data)

    @transaction.atomic
    def update_or_create(self, validated_data):
        channel = self.context["channel"]
        now = timezone.now()
        track_defaults = {
            "fid": validated_data["id"],
            "artist": channel.artist,
            "position": validated_data.get("position", 1),
            "disc_number": validated_data.get("disc", 1),
            "title": validated_data["name"],
            "copyright": validated_data.get("copyright"),
            "attributed_to": channel.attributed_to,
            "album": validated_data.get("album"),
            "creation_date": validated_data.get("published", now),
        }
        if validated_data.get("license"):
            track_defaults["license"] = licenses.match(validated_data["license"])

        track, created = music_models.Track.objects.update_or_create(
            artist__channel=channel, fid=validated_data["id"], defaults=track_defaults
        )

        if "image" in validated_data:
            new_value = self.validated_data["image"]
            common_utils.attach_file(
                track,
                "attachment_cover",
                {"url": new_value["url"], "mimetype": new_value.get("mediaType")}
                if new_value
                else None,
            )

        common_utils.attach_content(
            track, "description", validated_data.get("description")
        )

        tags = [t["name"] for t in validated_data.get("tags", []) or []]
        tags_models.set_tags(track, *tags)

        upload_defaults = {
            "fid": validated_data["id"],
            "track": track,
            "library": channel.library,
            "creation_date": validated_data.get("published", now),
            "duration": validated_data.get("duration"),
            "bitrate": validated_data["url"][0].get("bitrate"),
            "size": validated_data["url"][0].get("size"),
            "mimetype": validated_data["url"][0]["mediaType"],
            "source": validated_data["url"][0]["href"],
            "import_status": "finished",
        }
        upload, created = music_models.Upload.objects.update_or_create(
            fid=validated_data["id"], defaults=upload_defaults
        )
        return upload

    def create(self, validated_data):
        return self.update_or_create(validated_data)


class ChannelCreateUploadSerializer(jsonld.JsonLdSerializer):
    object = serializers.DictField()

    class Meta:
        jsonld_mapping = {
            "object": jsonld.first_obj(contexts.AS.object),
        }

    def to_representation(self, upload):
        payload = {
            "@context": jsonld.get_default_context(),
            "type": self.context.get("type", "Create"),
            "id": utils.full_url(
                reverse(
                    "federation:music:uploads-activity", kwargs={"uuid": upload.uuid}
                )
            ),
            "actor": upload.library.channel.actor.fid,
            "object": ChannelUploadSerializer(
                upload, context={"include_ap_context": False}
            ).data,
        }
        if self.context.get("activity_id_suffix"):
            payload["id"] = os.path.join(
                payload["id"], self.context["activity_id_suffix"]
            )

        return payload

    def validate(self, validated_data):
        serializer = ChannelUploadSerializer(
            data=validated_data["object"], context=self.context, jsonld_expand=False
        )
        serializer.is_valid(raise_exception=True)
        return {"audio_serializer": serializer}

    def save(self, **kwargs):
        return self.validated_data["audio_serializer"].save(**kwargs)


class DeleteSerializer(jsonld.JsonLdSerializer):
    object = serializers.URLField(max_length=500)
    type = serializers.ChoiceField(choices=[contexts.AS.Delete])

    class Meta:
        jsonld_mapping = {"object": jsonld.first_id(contexts.AS.object)}

    def validate_object(self, url):
        try:
            obj = utils.get_object_by_fid(url)
        except utils.ObjectDoesNotExist:
            raise serializers.ValidationError("No object matching {}".format(url))
        if isinstance(obj, music_models.Upload):
            obj = obj.track

        return obj

    def validate(self, validated_data):
        if not utils.can_manage(
            validated_data["object"].attributed_to, self.context["actor"]
        ):
            raise serializers.ValidationError("You cannot delete this object")
        return validated_data


class IndexSerializer(jsonld.JsonLdSerializer):
    type = serializers.ChoiceField(
        choices=[contexts.AS.Collection, contexts.AS.OrderedCollection]
    )
    totalItems = serializers.IntegerField(min_value=0)
    id = serializers.URLField(max_length=500)
    first = serializers.URLField(max_length=500)
    last = serializers.URLField(max_length=500)

    class Meta:
        jsonld_mapping = PAGINATED_COLLECTION_JSONLD_MAPPING

    def to_representation(self, conf):
        paginator = Paginator(conf["items"], conf["page_size"])
        first = common_utils.set_query_parameter(conf["id"], page=1)
        current = first
        last = common_utils.set_query_parameter(conf["id"], page=paginator.num_pages)
        d = {
            "id": conf["id"],
            "totalItems": paginator.count,
            "type": "OrderedCollection",
            "current": current,
            "first": first,
            "last": last,
        }
        if self.context.get("include_ap_context", True):
            d["@context"] = jsonld.get_default_context()
        return d

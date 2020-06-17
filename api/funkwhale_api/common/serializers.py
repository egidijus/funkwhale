import collections
import io
import PIL
import os

from rest_framework import serializers

from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _

from . import models
from . import utils


class RelatedField(serializers.RelatedField):
    default_error_messages = {
        "does_not_exist": _("Object with {related_field_name}={value} does not exist."),
        "invalid": _("Invalid value."),
    }

    def __init__(self, related_field_name, serializer, **kwargs):
        self.related_field_name = related_field_name
        self.serializer = serializer
        self.filters = kwargs.pop("filters", None)
        self.queryset_filter = kwargs.pop("queryset_filter", None)
        try:
            kwargs["queryset"] = kwargs.pop("queryset")
        except KeyError:
            kwargs["queryset"] = self.serializer.Meta.model.objects.all()
        super().__init__(**kwargs)

    def get_filters(self, data):
        filters = {self.related_field_name: data}
        if self.filters:
            filters.update(self.filters(self.context))
        return filters

    def filter_queryset(self, queryset):
        if self.queryset_filter:
            queryset = self.queryset_filter(queryset, self.context)
        return queryset

    def to_internal_value(self, data):
        try:
            queryset = self.get_queryset()
            filters = self.get_filters(data)
            queryset = self.filter_queryset(queryset)
            return queryset.get(**filters)
        except ObjectDoesNotExist:
            self.fail(
                "does_not_exist",
                related_field_name=self.related_field_name,
                value=smart_text(data),
            )
        except (TypeError, ValueError):
            self.fail("invalid")

    def to_representation(self, obj):
        return self.serializer.to_representation(obj)

    def get_choices(self, cutoff=None):
        queryset = self.get_queryset()
        if queryset is None:
            # Ensure that field.choices returns something sensible
            # even when accessed with a read-only field.
            return {}

        if cutoff is not None:
            queryset = queryset[:cutoff]

        return collections.OrderedDict(
            [
                (
                    self.to_representation(item)[self.related_field_name],
                    self.display_value(item),
                )
                for item in queryset
                if self.serializer
            ]
        )


class Action(object):
    def __init__(self, name, allow_all=False, qs_filter=None):
        self.name = name
        self.allow_all = allow_all
        self.qs_filter = qs_filter

    def __repr__(self):
        return "<Action {}>".format(self.name)


class ActionSerializer(serializers.Serializer):
    """
    A special serializer that can operate on a list of objects
    and apply actions on it.
    """

    action = serializers.CharField(required=True)
    objects = serializers.JSONField(required=True)
    filters = serializers.DictField(required=False)
    actions = None
    pk_field = "pk"

    def __init__(self, *args, **kwargs):
        self.actions_by_name = {a.name: a for a in self.actions}
        self.queryset = kwargs.pop("queryset")
        if self.actions is None:
            raise ValueError(
                "You must declare a list of actions on " "the serializer class"
            )

        for action in self.actions_by_name.keys():
            handler_name = "handle_{}".format(action)
            assert hasattr(self, handler_name), "{} miss a {} method".format(
                self.__class__.__name__, handler_name
            )
        super().__init__(self, *args, **kwargs)

    def validate_action(self, value):
        try:
            return self.actions_by_name[value]
        except KeyError:
            raise serializers.ValidationError(
                "{} is not a valid action. Pick one of {}.".format(
                    value, ", ".join(self.actions_by_name.keys())
                )
            )

    def validate_objects(self, value):
        if value == "all":
            return self.queryset.all().order_by("id")
        if type(value) in [list, tuple]:
            return self.queryset.filter(
                **{"{}__in".format(self.pk_field): value}
            ).order_by(self.pk_field)

        raise serializers.ValidationError(
            "{} is not a valid value for objects. You must provide either a "
            'list of identifiers or the string "all".'.format(value)
        )

    def validate(self, data):
        allow_all = data["action"].allow_all
        if not allow_all and self.initial_data["objects"] == "all":
            raise serializers.ValidationError(
                "You cannot apply this action on all objects"
            )
        final_filters = data.get("filters", {}) or {}
        if self.filterset_class and final_filters:
            qs_filterset = self.filterset_class(final_filters, queryset=data["objects"])
            try:
                assert qs_filterset.form.is_valid()
            except (AssertionError, TypeError):
                raise serializers.ValidationError("Invalid filters")
            data["objects"] = qs_filterset.qs

        if data["action"].qs_filter:
            data["objects"] = data["action"].qs_filter(data["objects"])

        data["count"] = data["objects"].count()
        if data["count"] < 1:
            raise serializers.ValidationError("No object matching your request")
        return data

    def save(self):
        handler_name = "handle_{}".format(self.validated_data["action"].name)
        handler = getattr(self, handler_name)
        result = handler(self.validated_data["objects"])
        payload = {
            "updated": self.validated_data["count"],
            "action": self.validated_data["action"].name,
            "result": result,
        }
        return payload


def track_fields_for_update(*fields):
    """
    Apply this decorator to serializer to call function when specific values
    are updated on an object:

    .. code-block:: python

        @track_fields_for_update('privacy_level')
        class LibrarySerializer(serializers.ModelSerializer):
            def on_updated_privacy_level(self, obj, old_value, new_value):
                print('Do someting')
    """

    def decorator(serializer_class):
        original_update = serializer_class.update

        def new_update(self, obj, validated_data):
            tracked_fields_before = {f: getattr(obj, f) for f in fields}
            obj = original_update(self, obj, validated_data)
            tracked_fields_after = {f: getattr(obj, f) for f in fields}

            if tracked_fields_before != tracked_fields_after:
                self.on_updated_fields(obj, tracked_fields_before, tracked_fields_after)
            return obj

        serializer_class.update = new_update
        return serializer_class

    return decorator


class StripExifImageField(serializers.ImageField):
    def to_internal_value(self, data):
        file_obj = super().to_internal_value(data)

        image = PIL.Image.open(file_obj)
        data = list(image.getdata())
        image_without_exif = PIL.Image.new(image.mode, image.size)
        image_without_exif.putdata(data)

        with io.BytesIO() as output:
            image_without_exif.save(
                output,
                format=PIL.Image.EXTENSION[os.path.splitext(file_obj.name)[-1].lower()],
                quality=100,
            )
            content = output.getvalue()

        return SimpleUploadedFile(
            file_obj.name, content, content_type=file_obj.content_type
        )


from funkwhale_api.federation import serializers as federation_serializers  # noqa

TARGET_ID_TYPE_MAPPING = {
    "music.Track": ("id", "track"),
    "music.Artist": ("id", "artist"),
    "music.Album": ("id", "album"),
}


class APIMutationSerializer(serializers.ModelSerializer):
    created_by = federation_serializers.APIActorSerializer(read_only=True)
    target = serializers.SerializerMethodField()

    class Meta:
        model = models.Mutation
        fields = [
            "fid",
            "uuid",
            "type",
            "creation_date",
            "applied_date",
            "is_approved",
            "is_applied",
            "created_by",
            "approved_by",
            "summary",
            "payload",
            "previous_state",
            "target",
        ]
        read_only_fields = [
            "uuid",
            "creation_date",
            "fid",
            "is_applied",
            "created_by",
            "approved_by",
            "previous_state",
        ]

    def get_target(self, obj):
        target = obj.target
        if not target:
            return

        id_field, type = TARGET_ID_TYPE_MAPPING[target._meta.label]
        return {"type": type, "id": getattr(target, id_field), "repr": str(target)}

    def validate_type(self, value):
        if value not in self.context["registry"]:
            raise serializers.ValidationError("Invalid mutation type {}".format(value))
        return value


class AttachmentSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(read_only=True)
    size = serializers.IntegerField(read_only=True)
    mimetype = serializers.CharField(read_only=True)
    creation_date = serializers.DateTimeField(read_only=True)
    file = StripExifImageField(write_only=True)
    urls = serializers.SerializerMethodField()

    def get_urls(self, o):
        urls = {}
        urls["source"] = o.url
        urls["original"] = o.download_url_original
        urls["medium_square_crop"] = o.download_url_medium_square_crop
        return urls

    def to_representation(self, o):
        repr = super().to_representation(o)
        # XXX: BACKWARD COMPATIBILITY
        # having the attachment urls in a nested JSON obj is better,
        # but we can't do this without breaking clients
        # So we extract the urls and include these in the parent payload
        repr.update({k: v for k, v in repr["urls"].items() if k != "source"})
        # also, our legacy images had lots of variations (400x400, 200x200, 50x50)
        # but we removed some of these, so we emulate these by hand (by redirecting)
        # to actual, existing attachment variations
        repr["square_crop"] = repr["medium_square_crop"]
        repr["small_square_crop"] = repr["medium_square_crop"]
        return repr

    def create(self, validated_data):
        return models.Attachment.objects.create(
            file=validated_data["file"], actor=validated_data["actor"]
        )


class ContentSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=models.CONTENT_TEXT_MAX_LENGTH)
    content_type = serializers.ChoiceField(choices=models.CONTENT_TEXT_SUPPORTED_TYPES,)
    html = serializers.SerializerMethodField()

    def get_html(self, o):
        return utils.render_html(o.text, o.content_type)


class NullToEmptDict(object):
    def get_attribute(self, o):
        attr = super().get_attribute(o)
        if attr is None:
            return {}
        return attr

    def to_representation(self, v):
        if not v:
            return v
        return super().to_representation(v)


class PodPluginSerializer(serializers.Serializer):
    code = serializers.CharField(read_only=True)
    enabled = serializers.BooleanField()
    conf = serializers.JSONField()
    label = serializers.SerializerMethodField()

    class Meta:
        fields = [
            "code",
            "label",
            "enabled",
            "conf",
        ]

    def get_label(self, o):
        return o.plugin.verbose_name

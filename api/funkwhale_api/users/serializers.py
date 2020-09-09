import re

from django.core import validators
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _

from django.contrib import auth

from allauth.account import models as allauth_models
from rest_auth.serializers import PasswordResetSerializer as PRS
from rest_auth.registration.serializers import RegisterSerializer as RS, get_adapter
from rest_framework import serializers
from rest_framework_jwt import serializers as jwt_serializers

from funkwhale_api.activity import serializers as activity_serializers
from funkwhale_api.common import authentication
from funkwhale_api.common import models as common_models
from funkwhale_api.common import preferences
from funkwhale_api.common import serializers as common_serializers
from funkwhale_api.common import utils as common_utils
from funkwhale_api.federation import models as federation_models
from funkwhale_api.moderation import models as moderation_models
from funkwhale_api.moderation import tasks as moderation_tasks
from funkwhale_api.moderation import utils as moderation_utils

from . import adapters
from . import models
from . import authentication as users_authentication


@deconstructible
class ASCIIUsernameValidator(validators.RegexValidator):
    regex = r"^[\w]+$"
    message = _(
        "Enter a valid username. This value may contain only English letters, "
        "numbers, and _ characters."
    )
    flags = re.ASCII


username_validators = [ASCIIUsernameValidator()]
NOOP = object()


class JSONWebTokenSerializer(jwt_serializers.JSONWebTokenSerializer):
    def validate(self, data):
        try:
            return super().validate(data)
        except authentication.UnverifiedEmail as e:
            authentication.send_email_confirmation(self.context["request"], e.user)
            raise serializers.ValidationError("Please verify your email address.")


class RegisterSerializer(RS):
    invitation = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )

    def __init__(self, *args, **kwargs):
        self.approval_enabled = preferences.get("moderation__signup_approval_enabled")
        super().__init__(*args, **kwargs)
        if self.approval_enabled:
            customization = preferences.get("moderation__signup_form_customization")
            self.fields[
                "request_fields"
            ] = moderation_utils.get_signup_form_additional_fields_serializer(
                customization
            )

    def validate_invitation(self, value):
        if not value:
            return

        try:
            return models.Invitation.objects.open().get(code__iexact=value)
        except models.Invitation.DoesNotExist:
            raise serializers.ValidationError("Invalid invitation code")

    def validate(self, validated_data):
        data = super().validate(validated_data)
        # we create a fake user obj with validated data so we can validate
        # password properly (we have a password validator that requires
        # a user object)
        user = models.User(username=data["username"], email=data["email"])
        get_adapter().clean_password(data["password1"], user)
        return data

    def validate_username(self, value):
        username = super().validate_username(value)
        duplicates = federation_models.Actor.objects.local().filter(
            preferred_username__iexact=username
        )
        if duplicates.exists():
            raise serializers.ValidationError(
                "A user with that username already exists."
            )
        return username

    def save(self, request):
        user = super().save(request)
        update_fields = ["actor"]
        user.actor = models.create_actor(user)
        user_request = None
        if self.approval_enabled:
            # manually approve users
            user.is_active = False
            user_request = moderation_models.UserRequest.objects.create(
                submitter=user.actor,
                type="signup",
                metadata=self.validated_data.get("request_fields", None) or None,
            )
            update_fields.append("is_active")
        if self.validated_data.get("invitation"):
            user.invitation = self.validated_data.get("invitation")
            update_fields.append("invitation")
        user.save(update_fields=update_fields)
        if user_request:
            common_utils.on_commit(
                moderation_tasks.user_request_handle.delay,
                user_request_id=user_request.pk,
                new_status=user_request.status,
            )

        return user


class UserActivitySerializer(activity_serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    name = serializers.CharField(source="username")
    local_id = serializers.CharField(source="username")

    class Meta:
        model = models.User
        fields = ["id", "local_id", "name", "type"]

    def get_type(self, obj):
        return "Person"


class UserBasicSerializer(serializers.ModelSerializer):
    avatar = common_serializers.AttachmentSerializer(source="get_avatar")

    class Meta:
        model = models.User
        fields = ["id", "username", "name", "date_joined", "avatar"]


class UserWriteSerializer(serializers.ModelSerializer):
    summary = common_serializers.ContentSerializer(required=False, allow_null=True)
    avatar = common_serializers.RelatedField(
        "uuid",
        queryset=common_models.Attachment.objects.all().local().attached(False),
        serializer=None,
        queryset_filter=lambda qs, context: qs.filter(
            actor=context["request"].user.actor
        ),
        write_only=True,
    )

    class Meta:
        model = models.User
        fields = [
            "name",
            "privacy_level",
            "avatar",
            "instance_support_message_display_date",
            "funkwhale_support_message_display_date",
            "summary",
        ]

    def update(self, obj, validated_data):
        if not obj.actor:
            obj.create_actor()
        summary = validated_data.pop("summary", NOOP)
        avatar = validated_data.pop("avatar", NOOP)

        obj = super().update(obj, validated_data)

        if summary != NOOP:
            common_utils.attach_content(obj.actor, "summary_obj", summary)
        if avatar != NOOP:
            obj.actor.attachment_icon = avatar
            obj.actor.save(update_fields=["attachment_icon"])
        return obj

    def to_representation(self, instance):
        r = super().to_representation(instance)
        r["avatar"] = common_serializers.AttachmentSerializer(
            instance.get_avatar()
        ).data
        return r


class UserReadSerializer(serializers.ModelSerializer):

    permissions = serializers.SerializerMethodField()
    full_username = serializers.SerializerMethodField()
    avatar = common_serializers.AttachmentSerializer(source="get_avatar")

    class Meta:
        model = models.User
        fields = [
            "id",
            "username",
            "full_username",
            "name",
            "email",
            "is_staff",
            "is_superuser",
            "permissions",
            "date_joined",
            "privacy_level",
            "avatar",
        ]

    def get_permissions(self, o):
        return o.get_permissions()

    def get_full_username(self, o):
        if o.actor:
            return o.actor.full_username


class MeSerializer(UserReadSerializer):
    quota_status = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    tokens = serializers.SerializerMethodField()

    class Meta(UserReadSerializer.Meta):
        fields = UserReadSerializer.Meta.fields + [
            "quota_status",
            "instance_support_message_display_date",
            "funkwhale_support_message_display_date",
            "summary",
            "tokens",
            "settings",
        ]

    def get_quota_status(self, o):
        return o.get_quota_status() if o.actor else 0

    def get_summary(self, o):
        if not o.actor or not o.actor.summary_obj:
            return
        return common_serializers.ContentSerializer(o.actor.summary_obj).data

    def get_tokens(self, o):
        return {
            "listen": users_authentication.generate_scoped_token(
                user_id=o.pk, user_secret=o.secret_key, scopes=["read:libraries"]
            )
        }


class PasswordResetSerializer(PRS):
    def get_email_options(self):
        return {"extra_email_context": adapters.get_email_context()}


class UserDeleteSerializer(serializers.Serializer):
    password = serializers.CharField()
    confirm = serializers.BooleanField()

    def validate_password(self, value):
        if not self.instance.check_password(value):
            raise serializers.ValidationError("Invalid password")

    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError("Please confirm deletion")
        return value


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        user = auth.authenticate(request=self.context.get("request"), **data)
        if not user:
            raise serializers.ValidationError(
                "Unable to log in with provided credentials"
            )

        if not user.is_active:
            raise serializers.ValidationError("This account was disabled")

        return user

    def save(self, request):
        return auth.login(request, self.validated_data)


class UserChangeEmailSerializer(serializers.Serializer):
    password = serializers.CharField()
    email = serializers.EmailField()

    def validate_password(self, value):
        if not self.instance.check_password(value):
            raise serializers.ValidationError("Invalid password")

    def validate_email(self, value):
        if (
            allauth_models.EmailAddress.objects.filter(email__iexact=value)
            .exclude(user=self.context["user"])
            .exists()
        ):
            raise serializers.ValidationError("This email address is already in use")
        return value

    def save(self, request):
        current, _ = allauth_models.EmailAddress.objects.get_or_create(
            user=request.user,
            email=request.user.email,
            defaults={"verified": False, "primary": True},
        )
        current.change(request, self.validated_data["email"], confirm=True)

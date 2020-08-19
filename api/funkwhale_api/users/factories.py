import pytz
import factory
from django.contrib.auth.models import Permission
from django.utils import timezone
from funkwhale_api.factories import ManyToManyFromList, registry, NoUpdateOnCreate

from . import models


@registry.register
class GroupFactory(NoUpdateOnCreate, factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: "group-{0}".format(n))

    class Meta:
        model = "auth.Group"

    @factory.post_generation
    def perms(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            perms = [
                Permission.objects.get(
                    content_type__app_label=p.split(".")[0], codename=p.split(".")[1]
                )
                for p in extracted
            ]
            # A list of permissions were passed in, use them
            self.permissions.add(*perms)


@registry.register
class EmailAddressFactory(NoUpdateOnCreate, factory.django.DjangoModelFactory):
    verified = False
    primary = True

    class Meta:
        model = "account.EmailAddress"


@registry.register
class EmailConfirmationFactory(NoUpdateOnCreate, factory.django.DjangoModelFactory):
    email_address = factory.SubFactory(EmailAddressFactory)

    class Meta:
        model = "account.EmailConfirmation"


@registry.register
class InvitationFactory(NoUpdateOnCreate, factory.django.DjangoModelFactory):
    owner = factory.LazyFunction(lambda: UserFactory())

    class Meta:
        model = "users.Invitation"

    class Params:
        expired = factory.Trait(expiration_date=factory.LazyFunction(timezone.now))


class PasswordSetter(factory.PostGenerationMethodCall):
    def call(self, instance, step, context):
        if context.value_provided and context.value is None:
            # disable setting the password, it's set by hand outside of the factory
            return

        return super().call(instance, step, context)


@registry.register
class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Faker("user_name")
    email = factory.Faker("email")
    password = password = PasswordSetter("set_password", "test")
    subsonic_api_token = None
    groups = ManyToManyFromList("groups")
    avatar = factory.django.ImageField()

    class Meta:
        model = "users.User"
        django_get_or_create = ("username",)

    class Params:
        invited = factory.Trait(invitation=factory.SubFactory(InvitationFactory))

    @factory.post_generation
    def perms(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            perms = [
                Permission.objects.get(
                    content_type__app_label=p.split(".")[0], codename=p.split(".")[1]
                )
                for p in extracted
            ]
            # A list of permissions were passed in, use them
            self.user_permissions.add(*perms)

    @factory.post_generation
    def with_actor(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.actor = models.create_actor(self)
        self.save(update_fields=["actor"])
        return self.actor

    @factory.post_generation
    def verified_email(self, create, extracted, **kwargs):
        if not create or extracted is None:
            return
        return EmailConfirmationFactory(
            email_address__verified=extracted,
            email_address__email=self.email,
            email_address__user=self,
        )


@registry.register(name="users.SuperUser")
class SuperUserFactory(UserFactory):
    is_staff = True
    is_superuser = True


@registry.register
class ApplicationFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("name")
    redirect_uris = factory.Faker("url")
    token = factory.Faker("uuid4")
    client_type = models.Application.CLIENT_CONFIDENTIAL
    authorization_grant_type = models.Application.GRANT_AUTHORIZATION_CODE
    scope = "read"

    class Meta:
        model = "users.Application"


@registry.register
class GrantFactory(factory.django.DjangoModelFactory):
    application = factory.SubFactory(ApplicationFactory)
    scope = factory.SelfAttribute(".application.scope")
    redirect_uri = factory.SelfAttribute(".application.redirect_uris")
    user = factory.SubFactory(UserFactory)
    expires = factory.Faker("future_datetime", end_date="+15m")
    code = factory.Faker("uuid4")

    class Meta:
        model = "users.Grant"


@registry.register
class AccessTokenFactory(factory.django.DjangoModelFactory):
    application = factory.SubFactory(ApplicationFactory)
    user = factory.SubFactory(UserFactory)
    expires = factory.Faker("future_datetime", tzinfo=pytz.UTC)
    token = factory.Faker("uuid4")
    scope = "read"

    class Meta:
        model = "users.AccessToken"


@registry.register
class RefreshTokenFactory(factory.django.DjangoModelFactory):
    application = factory.SubFactory(ApplicationFactory)
    user = factory.SubFactory(UserFactory)
    token = factory.Faker("uuid4")

    class Meta:
        model = "users.RefreshToken"

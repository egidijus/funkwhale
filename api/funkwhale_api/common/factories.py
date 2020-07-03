import factory

from funkwhale_api.factories import registry, NoUpdateOnCreate

from funkwhale_api.federation import factories as federation_factories


@registry.register
class MutationFactory(NoUpdateOnCreate, factory.django.DjangoModelFactory):
    fid = factory.Faker("federation_url")
    uuid = factory.Faker("uuid4")
    created_by = factory.SubFactory(federation_factories.ActorFactory)
    summary = factory.Faker("paragraph")
    type = "update"

    class Meta:
        model = "common.Mutation"


@registry.register
class AttachmentFactory(NoUpdateOnCreate, factory.django.DjangoModelFactory):
    url = factory.Faker("federation_url")
    uuid = factory.Faker("uuid4")
    actor = factory.SubFactory(federation_factories.ActorFactory)
    file = factory.django.ImageField()

    class Meta:
        model = "common.Attachment"


@registry.register
class CommonFactory(NoUpdateOnCreate, factory.django.DjangoModelFactory):
    text = factory.Faker("paragraph")
    content_type = "text/plain"

    class Meta:
        model = "common.Content"


@registry.register
class PluginConfiguration(NoUpdateOnCreate, factory.django.DjangoModelFactory):
    code = "test"
    conf = {"foo": "bar"}

    class Meta:
        model = "common.PluginConfiguration"

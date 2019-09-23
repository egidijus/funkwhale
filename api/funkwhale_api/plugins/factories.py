import factory

from funkwhale_api.factories import registry, NoUpdateOnCreate

from funkwhale_api.users.factories import UserFactory


@registry.register
class PluginFactory(factory.django.DjangoModelFactory):
    is_enabled = True
    config = factory.Faker("pydict", nb_elements=3)

    class Meta:
        model = "plugins.Plugin"

    @factory.post_generation
    def refresh(self, created, *args, **kwargs):
        """
        Needed to ensure we have JSON serialized value in the config field
        """
        if created:
            self.refresh_from_db()


@registry.register
class UserPluginFactory(factory.django.DjangoModelFactory):
    is_enabled = True
    user = factory.SubFactory(UserFactory)
    plugin = factory.SubFactory(PluginFactory)
    config = factory.Faker("pydict", nb_elements=3)

    class Meta:
        model = "plugins.UserPlugin"

    @factory.post_generation
    def refresh(self, created, *args, **kwargs):
        """
        Needed to ensure we have JSON serialized value in the config field
        """
        if created:
            self.refresh_from_db()

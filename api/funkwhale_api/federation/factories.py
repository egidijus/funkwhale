import uuid

import factory
import requests
import requests_http_signature
from django.conf import settings
from django.utils import timezone
from django.utils.http import http_date

from funkwhale_api.factories import registry, NoUpdateOnCreate
from funkwhale_api.users import factories as user_factories

from . import keys, models

registry.register(keys.get_key_pair, name="federation.KeyPair")


@registry.register(name="federation.SignatureAuth")
class SignatureAuthFactory(factory.Factory):
    algorithm = "rsa-sha256"
    key = factory.LazyFunction(lambda: keys.get_key_pair()[0])
    key_id = factory.Faker("url")
    headers = ["(request-target)", "user-agent", "host", "date", "accept"]

    class Meta:
        model = requests_http_signature.HTTPSignatureHeaderAuth


@registry.register(name="federation.SignedRequest")
class SignedRequestFactory(factory.Factory):
    url = factory.Faker("url")
    method = "get"
    auth = factory.SubFactory(SignatureAuthFactory)

    class Meta:
        model = requests.Request

    @factory.post_generation
    def headers(self, create, extracted, **kwargs):
        default_headers = {
            "User-Agent": "Test",
            "Host": "test.host",
            "Date": http_date(timezone.now().timestamp()),
            "Accept": "application/activity+json",
        }
        if extracted:
            default_headers.update(extracted)
        self.headers.update(default_headers)


@registry.register(name="federation.Link")
class LinkFactory(factory.Factory):
    type = "Link"
    href = factory.Faker("url")
    mediaType = "text/html"

    class Meta:
        model = dict

    class Params:
        audio = factory.Trait(mediaType=factory.Iterator(["audio/mp3", "audio/ogg"]))


def create_user(actor):
    return user_factories.UserFactory(actor=actor)


@registry.register
class DomainFactory(NoUpdateOnCreate, factory.django.DjangoModelFactory):
    name = factory.Faker("domain_name")
    nodeinfo_fetch_date = factory.LazyFunction(lambda: timezone.now())
    allowed = None

    class Meta:
        model = "federation.Domain"
        django_get_or_create = ("name",)

    @factory.post_generation
    def with_service_actor(self, create, extracted, **kwargs):
        if not create or not extracted:
            return

        self.service_actor = ActorFactory(domain=self)
        self.save(update_fields=["service_actor"])
        return self.service_actor


_CACHE = {}


def get_cached_key_pair():
    try:
        return _CACHE["keys"]
    except KeyError:
        _CACHE["keys"] = keys.get_key_pair()
    return _CACHE["keys"]


@registry.register
class ActorFactory(NoUpdateOnCreate, factory.DjangoModelFactory):
    public_key = None
    private_key = None
    preferred_username = factory.Faker("user_name")
    summary = factory.Faker("paragraph")
    domain = factory.SubFactory(DomainFactory)
    fid = factory.LazyAttribute(
        lambda o: "https://{}/users/{}".format(o.domain.name, o.preferred_username)
    )
    followers_url = factory.LazyAttribute(
        lambda o: "https://{}/users/{}followers".format(
            o.domain.name, o.preferred_username
        )
    )
    inbox_url = factory.LazyAttribute(
        lambda o: "https://{}/users/{}/inbox".format(
            o.domain.name, o.preferred_username
        )
    )
    outbox_url = factory.LazyAttribute(
        lambda o: "https://{}/users/{}/outbox".format(
            o.domain.name, o.preferred_username
        )
    )
    keys = factory.LazyFunction(get_cached_key_pair)

    class Meta:
        model = models.Actor

    class Params:
        with_real_keys = factory.Trait(keys=factory.LazyFunction(keys.get_key_pair),)

    @factory.post_generation
    def local(self, create, extracted, **kwargs):
        if not extracted and not kwargs:
            return
        from funkwhale_api.users.factories import UserFactory

        self.domain = models.Domain.objects.get_or_create(
            name=settings.FEDERATION_HOSTNAME
        )[0]
        self.fid = "https://{}/actors/{}".format(self.domain, self.preferred_username)
        self.save(update_fields=["domain", "fid"])
        if not create:
            if extracted and hasattr(extracted, "pk"):
                extracted.actor = self
            else:
                UserFactory.build(actor=self, **kwargs)
        if extracted and hasattr(extracted, "pk"):
            extracted.actor = self
            extracted.save(update_fields=["user"])
        else:
            self.user = UserFactory(actor=self, **kwargs)


@registry.register
class FollowFactory(NoUpdateOnCreate, factory.DjangoModelFactory):
    target = factory.SubFactory(ActorFactory)
    actor = factory.SubFactory(ActorFactory)

    class Meta:
        model = models.Follow

    class Params:
        local = factory.Trait(actor=factory.SubFactory(ActorFactory, local=True))


@registry.register
class MusicLibraryFactory(NoUpdateOnCreate, factory.django.DjangoModelFactory):
    actor = factory.SubFactory(ActorFactory)
    privacy_level = "me"
    name = factory.Faker("sentence")
    description = factory.Faker("sentence")
    uploads_count = 0
    fid = factory.Faker("federation_url")
    followers_url = factory.LazyAttribute(
        lambda o: o.fid + "/followers" if o.fid else None
    )

    class Meta:
        model = "music.Library"

    class Params:
        local = factory.Trait(
            fid=None, actor=factory.SubFactory(ActorFactory, local=True)
        )


@registry.register
class LibraryScanFactory(NoUpdateOnCreate, factory.django.DjangoModelFactory):
    library = factory.SubFactory(MusicLibraryFactory)
    actor = factory.SubFactory(ActorFactory)
    total_files = factory.LazyAttribute(lambda o: o.library.uploads_count)

    class Meta:
        model = "music.LibraryScan"


@registry.register
class FetchFactory(NoUpdateOnCreate, factory.django.DjangoModelFactory):
    actor = factory.SubFactory(ActorFactory)

    class Meta:
        model = "federation.Fetch"


@registry.register
class ActivityFactory(NoUpdateOnCreate, factory.django.DjangoModelFactory):
    actor = factory.SubFactory(ActorFactory)
    url = factory.Faker("federation_url")
    payload = factory.LazyFunction(lambda: {"type": "Create"})

    class Meta:
        model = "federation.Activity"


@registry.register
class InboxItemFactory(NoUpdateOnCreate, factory.django.DjangoModelFactory):
    actor = factory.SubFactory(ActorFactory, local=True)
    activity = factory.SubFactory(ActivityFactory)
    type = "to"

    class Meta:
        model = "federation.InboxItem"


@registry.register
class DeliveryFactory(NoUpdateOnCreate, factory.django.DjangoModelFactory):
    activity = factory.SubFactory(ActivityFactory)
    inbox_url = factory.Faker("url")

    class Meta:
        model = "federation.Delivery"


@registry.register
class LibraryFollowFactory(NoUpdateOnCreate, factory.DjangoModelFactory):
    target = factory.SubFactory(MusicLibraryFactory)
    actor = factory.SubFactory(ActorFactory)

    class Meta:
        model = "federation.LibraryFollow"


class ArtistMetadataFactory(factory.Factory):
    name = factory.Faker("name")

    class Meta:
        model = dict

    class Params:
        musicbrainz = factory.Trait(musicbrainz_id=factory.Faker("uuid4"))


class ReleaseMetadataFactory(factory.Factory):
    title = factory.Faker("sentence")

    class Meta:
        model = dict

    class Params:
        musicbrainz = factory.Trait(musicbrainz_id=factory.Faker("uuid4"))


class RecordingMetadataFactory(factory.Factory):
    title = factory.Faker("sentence")

    class Meta:
        model = dict

    class Params:
        musicbrainz = factory.Trait(musicbrainz_id=factory.Faker("uuid4"))


@registry.register(name="federation.LibraryTrackMetadata")
class LibraryTrackMetadataFactory(factory.Factory):
    artist = factory.SubFactory(ArtistMetadataFactory)
    recording = factory.SubFactory(RecordingMetadataFactory)
    release = factory.SubFactory(ReleaseMetadataFactory)

    class Meta:
        model = dict


@registry.register(name="federation.Note")
class NoteFactory(factory.Factory):
    type = "Note"
    id = factory.Faker("url")
    published = factory.LazyFunction(lambda: timezone.now().isoformat())
    inReplyTo = None
    content = factory.Faker("sentence")

    class Meta:
        model = dict


@registry.register(name="federation.AudioMetadata")
class AudioMetadataFactory(factory.Factory):
    recording = factory.LazyAttribute(
        lambda o: "https://musicbrainz.org/recording/{}".format(uuid.uuid4())
    )
    artist = factory.LazyAttribute(
        lambda o: "https://musicbrainz.org/artist/{}".format(uuid.uuid4())
    )
    release = factory.LazyAttribute(
        lambda o: "https://musicbrainz.org/release/{}".format(uuid.uuid4())
    )
    bitrate = 42
    length = 43
    size = 44

    class Meta:
        model = dict


@registry.register(name="federation.Audio")
class AudioFactory(factory.Factory):
    type = "Audio"
    id = factory.Faker("federation_url")
    published = factory.LazyFunction(lambda: timezone.now().isoformat())
    actor = factory.Faker("federation_url")
    url = factory.SubFactory(LinkFactory, audio=True)
    metadata = factory.SubFactory(LibraryTrackMetadataFactory)

    class Meta:
        model = dict

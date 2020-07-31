import datetime
import uuid

import feedparser
import pytest
import pytz

from django.templatetags.static import static

from funkwhale_api.audio import serializers
from funkwhale_api.common import serializers as common_serializers
from funkwhale_api.common import utils as common_utils
from funkwhale_api.federation import actors
from funkwhale_api.federation import serializers as federation_serializers
from funkwhale_api.federation import utils as federation_utils
from funkwhale_api.music import serializers as music_serializers


def test_channel_serializer_create(factories, mocker):
    attributed_to = factories["federation.Actor"](local=True)
    attachment = factories["common.Attachment"](actor=attributed_to)
    request = mocker.Mock(user=mocker.Mock(actor=attributed_to))
    data = {
        "name": "My channel",
        "username": "mychannel",
        "description": {"text": "This is my channel", "content_type": "text/markdown"},
        "tags": ["hello", "world"],
        "content_category": "other",
        "cover": attachment.uuid,
    }

    serializer = serializers.ChannelCreateSerializer(
        data=data, context={"actor": attributed_to, "request": request}
    )
    assert serializer.is_valid(raise_exception=True) is True

    channel = serializer.save(attributed_to=attributed_to)

    assert channel.artist.name == data["name"]
    assert channel.artist.attributed_to == attributed_to
    assert (
        sorted(channel.artist.tagged_items.values_list("tag__name", flat=True))
        == data["tags"]
    )
    assert channel.artist.description.text == data["description"]["text"]
    assert channel.artist.attachment_cover == attachment
    assert channel.artist.content_category == data["content_category"]
    assert (
        channel.artist.description.content_type == data["description"]["content_type"]
    )
    assert channel.attributed_to == attributed_to
    assert channel.actor.preferred_username == data["username"]
    assert channel.actor.name == data["name"]
    assert channel.library.privacy_level == "everyone"
    assert channel.library.actor == attributed_to


def test_channel_serializer_create_honor_max_channels_setting(factories, preferences):
    preferences["audio__max_channels"] = 1
    attributed_to = factories["federation.Actor"](local=True)
    factories["audio.Channel"](attributed_to=attributed_to)
    data = {
        "name": "My channel",
        "username": "mychannel",
        "description": {"text": "This is my channel", "content_type": "text/markdown"},
        "tags": ["hello", "world"],
        "content_category": "other",
    }

    serializer = serializers.ChannelCreateSerializer(
        data=data, context={"actor": attributed_to}
    )
    with pytest.raises(serializers.serializers.ValidationError, match=r".*max.*"):
        assert serializer.is_valid(raise_exception=True)


def test_channel_serializer_create_validates_username_uniqueness(factories):
    attributed_to = factories["federation.Actor"](local=True)
    data = {
        "name": "My channel",
        "username": attributed_to.preferred_username.upper(),
        "description": {"text": "This is my channel", "content_type": "text/markdown"},
        "tags": ["hello", "world"],
        "content_category": "other",
    }

    serializer = serializers.ChannelCreateSerializer(
        data=data, context={"actor": attributed_to}
    )
    with pytest.raises(
        serializers.serializers.ValidationError, match=r".*username is already taken.*"
    ):
        assert serializer.is_valid(raise_exception=True)


def test_channel_serializer_create_validates_username_chars(factories):
    attributed_to = factories["federation.Actor"](local=True)
    data = {
        "name": "My channel",
        "username": "hello world",
        "description": {"text": "This is my channel", "content_type": "text/markdown"},
        "tags": ["hello", "world"],
        "content_category": "other",
    }

    serializer = serializers.ChannelCreateSerializer(
        data=data, context={"actor": attributed_to}
    )
    with pytest.raises(
        serializers.serializers.ValidationError, match=r".*Enter a valid username.*"
    ):
        assert serializer.is_valid(raise_exception=True)


def test_channel_serializer_create_validates_blacklisted_username(factories, settings):
    settings.ACCOUNT_USERNAME_BLACKLIST = ["forBidden"]
    attributed_to = factories["federation.Actor"](local=True)
    data = {
        "name": "My channel",
        "username": "FORBIDDEN",
        "description": {"text": "This is my channel", "content_type": "text/markdown"},
        "tags": ["hello", "world"],
        "content_category": "other",
    }

    serializer = serializers.ChannelCreateSerializer(
        data=data, context={"actor": attributed_to}
    )
    with pytest.raises(
        serializers.serializers.ValidationError, match=r".*username is already taken.*"
    ):
        assert serializer.is_valid(raise_exception=True)


def test_channel_serializer_create_podcast(factories):
    attributed_to = factories["federation.Actor"](local=True)

    data = {
        # TODO: cover
        "name": "My channel",
        "username": "mychannel",
        "description": {"text": "This is my channel", "content_type": "text/markdown"},
        "tags": ["hello", "world"],
        "content_category": "podcast",
        "metadata": {"itunes_category": "Sports", "language": "en"},
    }

    serializer = serializers.ChannelCreateSerializer(
        data=data, context={"actor": attributed_to}
    )
    assert serializer.is_valid(raise_exception=True) is True

    channel = serializer.save(attributed_to=attributed_to)
    assert channel.metadata == data["metadata"]


def test_channel_serializer_update(factories, mocker):
    channel = factories["audio.Channel"](
        artist__set_tags=["rock"], attributed_to__local=True
    )
    attributed_to = channel.attributed_to
    attachment = factories["common.Attachment"](actor=attributed_to)
    request = mocker.Mock(user=mocker.Mock(actor=attributed_to))
    data = {
        "name": "My channel",
        "description": {"text": "This is my channel", "content_type": "text/markdown"},
        "tags": ["hello", "world"],
        "content_category": "other",
        "cover": attachment.uuid,
    }

    serializer = serializers.ChannelUpdateSerializer(
        channel, data=data, context={"request": request}
    )
    assert serializer.is_valid(raise_exception=True) is True

    serializer.save()
    channel.refresh_from_db()

    assert channel.artist.name == data["name"]
    assert channel.artist.attachment_cover == attachment
    assert channel.artist.content_category == data["content_category"]
    assert (
        sorted(channel.artist.tagged_items.values_list("tag__name", flat=True))
        == data["tags"]
    )
    assert channel.artist.description.text == data["description"]["text"]
    assert channel.artist.description.content_type == "text/markdown"
    assert channel.actor.name == data["name"]


def test_channel_serializer_update_podcast(factories):
    channel = factories["audio.Channel"](artist__set_tags=["rock"])

    data = {
        # TODO: cover
        "name": "My channel",
        "description": {"text": "This is my channel", "content_type": "text/markdown"},
        "tags": ["hello", "world"],
        "content_category": "podcast",
        "metadata": {"language": "en", "itunes_category": "Sports"},
    }

    serializer = serializers.ChannelUpdateSerializer(channel, data=data)
    assert serializer.is_valid(raise_exception=True) is True

    serializer.save()
    channel.refresh_from_db()

    assert channel.metadata == data["metadata"]


def test_channel_serializer_representation(factories, to_api_date):
    content = factories["common.Content"]()
    channel = factories["audio.Channel"](artist__description=content)
    setattr(channel, "_downloads_count", 12)
    expected = {
        "artist": music_serializers.serialize_artist_simple(channel.artist),
        "uuid": str(channel.uuid),
        "creation_date": to_api_date(channel.creation_date),
        "actor": federation_serializers.APIActorSerializer(channel.actor).data,
        "attributed_to": federation_serializers.APIActorSerializer(
            channel.attributed_to
        ).data,
        "metadata": {},
        "rss_url": channel.get_rss_url(),
        "url": channel.actor.url,
        "downloads_count": 12,
    }
    expected["artist"]["description"] = common_serializers.ContentSerializer(
        content
    ).data

    assert serializers.ChannelSerializer(channel).data == expected


def test_channel_serializer_external_representation(factories, to_api_date):
    content = factories["common.Content"]()
    channel = factories["audio.Channel"](artist__description=content, external=True)

    expected = {
        "artist": music_serializers.serialize_artist_simple(channel.artist),
        "uuid": str(channel.uuid),
        "creation_date": to_api_date(channel.creation_date),
        "actor": None,
        "attributed_to": federation_serializers.APIActorSerializer(
            channel.attributed_to
        ).data,
        "metadata": {},
        "rss_url": channel.get_rss_url(),
        "url": channel.actor.url,
        "downloads_count": None,
    }
    expected["artist"]["description"] = common_serializers.ContentSerializer(
        content
    ).data

    assert serializers.ChannelSerializer(channel).data == expected


def test_channel_serializer_representation_subscriptions_count(factories, to_api_date):
    channel = factories["audio.Channel"]()
    factories["federation.Follow"](target=channel.actor)
    factories["federation.Follow"](target=channel.actor, approved=False)
    serializer = serializers.ChannelSerializer(
        channel, context={"subscriptions_count": True}
    )
    assert serializer.data["subscriptions_count"] == 1


def test_subscription_serializer(factories, to_api_date):
    subscription = factories["audio.Subscription"]()
    expected = {
        "channel": serializers.ChannelSerializer(subscription.target.channel).data,
        "uuid": str(subscription.uuid),
        "creation_date": to_api_date(subscription.creation_date),
        "approved": subscription.approved,
        "fid": subscription.fid,
    }

    assert serializers.SubscriptionSerializer(subscription).data == expected


def test_rss_item_serializer(factories):
    description = factories["common.Content"]()
    upload = factories["music.Upload"](
        playable=True,
        track__set_tags=["pop", "rock"],
        track__description=description,
        track__disc_number=4,
        track__position=42,
        track__with_cover=True,
    )
    setattr(
        upload.track,
        "_prefetched_tagged_items",
        upload.track.tagged_items.order_by("tag__name"),
    )
    expected = {
        "title": [{"value": upload.track.title}],
        "itunes:title": [{"value": upload.track.title}],
        "itunes:subtitle": [{"value": description.truncate(255)}],
        "itunes:summary": [{"cdata_value": description.rendered}],
        "description": [{"value": description.as_plain_text}],
        "guid": [{"cdata_value": str(upload.uuid), "isPermalink": "false"}],
        "pubDate": [{"value": serializers.rfc822_date(upload.creation_date)}],
        "itunes:duration": [{"value": serializers.rss_duration(upload.duration)}],
        "itunes:keywords": [{"value": "pop rock"}],
        "itunes:explicit": [{"value": "no"}],
        "itunes:episodeType": [{"value": "full"}],
        "itunes:season": [{"value": upload.track.disc_number}],
        "itunes:episode": [{"value": upload.track.position}],
        "itunes:image": [{"href": upload.track.attachment_cover.download_url_original}],
        "link": [{"value": federation_utils.full_url(upload.track.get_absolute_url())}],
        "enclosure": [
            {
                "url": federation_utils.full_url(upload.get_listen_url("mp3")),
                "length": upload.size,
                "type": "audio/mpeg",
            }
        ],
    }

    assert serializers.rss_serialize_item(upload) == expected


def test_rss_channel_serializer(factories):
    metadata = {
        "language": "fr",
        "itunes_category": "Parent",
        "itunes_subcategory": "Child",
        "copyright": "Myself",
        "owner_name": "Name",
        "owner_email": "name@domain.com",
        "explicit": True,
    }
    description = factories["common.Content"]()
    channel = factories["audio.Channel"](
        artist__set_tags=["pop", "rock"],
        artist__description=description,
        metadata=metadata,
        artist__with_cover=True,
    )
    setattr(
        channel.artist,
        "_prefetched_tagged_items",
        channel.artist.tagged_items.order_by("tag__name"),
    )

    expected = {
        "title": [{"value": channel.artist.name}],
        "language": [{"value": metadata["language"]}],
        "copyright": [{"value": metadata["copyright"]}],
        "itunes:subtitle": [{"value": description.truncate(255)}],
        "itunes:summary": [{"cdata_value": description.rendered}],
        "description": [{"value": description.as_plain_text}],
        "itunes:keywords": [{"value": "pop rock"}],
        "itunes:category": [
            {
                "text": metadata["itunes_category"],
                "itunes:category": [{"text": metadata["itunes_subcategory"]}],
            }
        ],
        "itunes:explicit": [{"value": "yes"}],
        "itunes:owner": [
            {
                "itunes:name": [{"value": metadata["owner_name"]}],
                "itunes:email": [{"value": metadata["owner_email"]}],
            }
        ],
        "itunes:author": [{"value": metadata["owner_name"]}],
        "itunes:type": [{"value": "episodic"}],
        "itunes:image": [
            {"href": channel.artist.attachment_cover.download_url_original}
        ],
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

    assert serializers.rss_serialize_channel(channel) == expected


def test_rss_channel_serializer_placeholder_image(factories):
    description = factories["common.Content"]()
    channel = factories["audio.Channel"](
        artist__set_tags=["pop", "rock"],
        artist__description=description,
        artist__attachment_cover=None,
    )
    setattr(
        channel.artist,
        "_prefetched_tagged_items",
        channel.artist.tagged_items.order_by("tag__name"),
    )

    expected = [
        {
            "href": federation_utils.full_url(
                static("images/podcasts-cover-placeholder.png")
            )
        }
    ]

    assert serializers.rss_serialize_channel(channel)["itunes:image"] == expected


def test_serialize_full_channel(factories):
    channel = factories["audio.Channel"]()
    upload1 = factories["music.Upload"](playable=True)
    upload2 = factories["music.Upload"](playable=True)

    expected = serializers.rss_serialize_channel(channel)
    expected["item"] = [
        serializers.rss_serialize_item(upload1),
        serializers.rss_serialize_item(upload2),
    ]
    expected = {"channel": expected}

    result = serializers.rss_serialize_channel_full(
        channel=channel, uploads=[upload1, upload2]
    )

    assert result == expected


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (0, "00:00:00"),
        (None, "00:00:00"),
        (61, "00:01:01"),
        (3601, "01:00:01"),
        (7345, "02:02:25"),
    ],
)
def test_rss_duration(seconds, expected):
    assert serializers.rss_duration(seconds) == expected


@pytest.mark.parametrize(
    "dt, expected",
    [
        (
            datetime.datetime(2020, 1, 30, 6, 0, 49, tzinfo=pytz.UTC),
            "Thu, 30 Jan 2020 06:00:49 +0000",
        ),
    ],
)
def test_rfc822_date(dt, expected):
    assert serializers.rfc822_date(dt) == expected


def test_channel_metadata_serializer_validation():
    payload = {
        "language": "fr",
        "copyright": "Me",
        "owner_email": "contact@me.com",
        "owner_name": "Me",
        "itunes_category": "Health & Fitness",
        "itunes_subcategory": "Sexuality",
        "unknown_key": "noop",
    }

    serializer = serializers.ChannelMetadataSerializer(data=payload)

    assert serializer.is_valid(raise_exception=True) is True

    payload.pop("unknown_key")

    assert serializer.validated_data == payload


def test_rss_feed_serializer_create(db, now):
    rss_url = "http://example.rss/"

    xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Hello</title>
                <description>Description</description>
                <link>http://public.url</link>
                <atom:link rel="self" type="application/rss+xml" href="http://real.rss.url"/>
                <lastBuildDate>Wed, 11 Mar 2020 16:01:08 GMT</lastBuildDate>
                <pubDate>Wed, 11 Mar 2020 16:00:00 GMT</pubDate>
                <ttl>30</ttl>
                <language>en</language>
                <copyright>2019 Tests</copyright>
                <itunes:keywords>pop rock</itunes:keywords>
                <image>
                    <url>
                        https://image.url
                    </url>
                    <title>Image caption</title>
                </image>
                <itunes:image href="https://image.url"/>
                <itunes:subtitle>Subtitle</itunes:subtitle>
                <itunes:type>episodic</itunes:type>
                <itunes:author>Author</itunes:author>
                <itunes:summary><![CDATA[Some content]]></itunes:summary>
                <itunes:owner>
                    <itunes:name>Name</itunes:name>
                    <itunes:email>email@domain</itunes:email>
                </itunes:owner>
                <itunes:explicit>yes</itunes:explicit>
                <itunes:keywords/>
                <itunes:category text="Business">
                    <itunes:category text="Entrepreneurship">
                </itunes:category>
            </channel>
        </rss>
    """
    parsed_feed = feedparser.parse(xml_payload)
    serializer = serializers.RssFeedSerializer(data=parsed_feed.feed)

    assert serializer.is_valid(raise_exception=True) is True

    channel = serializer.save(rss_url)

    assert channel.rss_url == "http://real.rss.url"
    assert channel.attributed_to == actors.get_service_actor()
    assert channel.library.actor == actors.get_service_actor()
    assert channel.artist.name == "Hello"
    assert channel.artist.attributed_to == actors.get_service_actor()
    assert channel.artist.description.content_type == "text/plain"
    assert channel.artist.description.text == "Some content"
    assert channel.artist.attachment_cover.url == "https://image.url"
    assert channel.artist.get_tags() == ["pop", "rock"]
    assert channel.actor.url == "http://public.url"
    assert channel.actor.last_fetch_date == now
    assert channel.metadata == {
        "explicit": True,
        "copyright": "2019 Tests",
        "owner_name": "Name",
        "owner_email": "email@domain",
        "itunes_category": "Business",
        "itunes_subcategory": "Entrepreneurship",
        "language": "en",
    }


def test_rss_feed_serializer_update(factories, now):
    rss_url = "http://example.rss/"
    channel = factories["audio.Channel"](rss_url=rss_url, external=True)

    xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Hello</title>
                <description>Description</description>
                <link>http://public.url</link>
                <atom:link rel="self" type="application/rss+xml" href="http://real.rss.url"/>
                <lastBuildDate>Wed, 11 Mar 2020 16:01:08 GMT</lastBuildDate>
                <pubDate>Wed, 11 Mar 2020 16:00:00 GMT</pubDate>
                <ttl>30</ttl>
                <language>en</language>
                <copyright>2019 Tests</copyright>
                <itunes:keywords>pop rock</itunes:keywords>
                <image>
                    <url>
                        https://image.url
                    </url>
                    <title>Image caption</title>
                </image>
                <itunes:image href="https://image.url"/>
                <itunes:subtitle>Subtitle</itunes:subtitle>
                <itunes:type>episodic</itunes:type>
                <itunes:author>Author</itunes:author>
                <itunes:summary><![CDATA[Some content]]></itunes:summary>
                <itunes:owner>
                    <itunes:name>Name</itunes:name>
                    <itunes:email>email@domain</itunes:email>
                </itunes:owner>
                <itunes:explicit>yes</itunes:explicit>
                <itunes:keywords/>
                <itunes:category text="Business">
                    <itunes:category text="Entrepreneurship">
                </itunes:category>
            </channel>
        </rss>
    """
    parsed_feed = feedparser.parse(xml_payload)
    serializer = serializers.RssFeedSerializer(data=parsed_feed.feed)

    assert serializer.is_valid(raise_exception=True) is True

    serializer.save(rss_url)

    channel.refresh_from_db()

    assert channel.rss_url == "http://real.rss.url"
    assert channel.attributed_to == actors.get_service_actor()
    assert channel.library.actor == actors.get_service_actor()
    assert channel.library.fid is not None
    assert channel.artist.name == "Hello"
    assert channel.artist.attributed_to == actors.get_service_actor()
    assert channel.artist.description.content_type == "text/plain"
    assert channel.artist.description.text == "Some content"
    assert channel.artist.attachment_cover.url == "https://image.url"
    assert channel.artist.get_tags() == ["pop", "rock"]
    assert channel.actor.url == "http://public.url"
    assert channel.actor.last_fetch_date == now
    assert channel.metadata == {
        "explicit": True,
        "copyright": "2019 Tests",
        "owner_name": "Name",
        "owner_email": "email@domain",
        "itunes_category": "Business",
        "itunes_subcategory": "Entrepreneurship",
        "language": "en",
    }


def test_rss_feed_item_serializer_create(factories):
    rss_url = "http://example.rss/"
    channel = factories["audio.Channel"](rss_url=rss_url, external=True)

    xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Hello</title>
                <description>Description</description>
                <link>http://public.url</link>
                <atom:link rel="self" type="application/rss+xml" href="http://real.rss.url"/>
                <item>
                    <title>Episode 33</title>
                    <itunes:subtitle>Subtitle</itunes:subtitle>
                    <itunes:summary><![CDATA[<p>Html content</p>]]></itunes:summary>
                    <guid isPermaLink="false"><![CDATA[16f66fff-41ae-4a1c-9101-2746218c4f32]]></guid>
                    <pubDate>Wed, 11 Mar 2020 16:00:00 GMT</pubDate>
                    <itunes:duration>00:22:37</itunes:duration>
                    <itunes:keywords>pop rock</itunes:keywords>
                    <itunes:season>2</itunes:season>
                    <itunes:episode>33</itunes:episode>
                    <itunes:image href="https://image.url/" />
                    <description><![CDATA[Html content]]></description>
                    <link>http://public.url/</link>
                    <enclosure url="https://file.domain/audio.mp3" length="54315884" type="audio/mpeg"/>
                </item>
            </channel>
        </rss>
    """
    parsed_feed = feedparser.parse(xml_payload)
    entry = parsed_feed.entries[0]
    serializer = serializers.RssFeedItemSerializer(data=entry)

    assert serializer.is_valid(raise_exception=True) is True

    upload = serializer.save(channel, copyright="test something")

    expected_uuid = uuid.uuid3(
        uuid.NAMESPACE_URL,
        "rss://{}-16f66fff-41ae-4a1c-9101-2746218c4f32".format(channel.pk),
    )
    assert upload.library == channel.library
    assert upload.import_status == "finished"
    assert upload.source == "https://file.domain/audio.mp3"
    assert upload.size == 54315884
    assert upload.duration == 1357
    assert upload.mimetype == "audio/mpeg"
    assert upload.track.uuid == expected_uuid
    assert upload.track.artist == channel.artist
    assert upload.track.copyright == "test something"
    assert upload.track.position == 33
    assert upload.track.disc_number == 2
    assert upload.track.creation_date == datetime.datetime(2020, 3, 11, 16).replace(
        tzinfo=pytz.utc
    )
    assert upload.track.get_tags() == ["pop", "rock"]
    assert upload.track.attachment_cover.url == "https://image.url/"
    assert upload.track.description.text == "<p>Html content</p>"
    assert upload.track.description.content_type == "text/html"


def test_rss_feed_item_serializer_update(factories):
    rss_url = "http://example.rss/"
    channel = factories["audio.Channel"](rss_url=rss_url, external=True)
    expected_uuid = uuid.uuid3(
        uuid.NAMESPACE_URL,
        "rss://{}-16f66fff-41ae-4a1c-9101-2746218c4f32".format(channel.pk),
    )
    upload = factories["music.Upload"](
        track__uuid=expected_uuid,
        source="https://file.domain/audio.mp3",
        library=channel.library,
        track__artist=channel.artist,
    )
    track = upload.track

    xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Hello</title>
                <description>Description</description>
                <link>http://public.url</link>
                <atom:link rel="self" type="application/rss+xml" href="http://real.rss.url"/>
                <item>
                    <title>Episode 33</title>
                    <itunes:subtitle>Subtitle</itunes:subtitle>
                    <itunes:summary><![CDATA[<p>Html content</p>]]></itunes:summary>
                    <guid isPermaLink="false"><![CDATA[16f66fff-41ae-4a1c-9101-2746218c4f32]]></guid>
                    <pubDate>Wed, 11 Mar 2020 16:00:00 GMT</pubDate>
                    <itunes:duration>00:22:37</itunes:duration>
                    <itunes:keywords>pop rock</itunes:keywords>
                    <itunes:season>2</itunes:season>
                    <itunes:episode>33</itunes:episode>
                    <itunes:image href="https://image.url/" />
                    <description><![CDATA[Html content]]></description>
                    <link>http://public.url/</link>
                    <enclosure url="https://file.domain/audio.mp3" length="54315884" type="audio/mpeg"/>
                </item>
            </channel>
        </rss>
    """
    parsed_feed = feedparser.parse(xml_payload)
    entry = parsed_feed.entries[0]
    serializer = serializers.RssFeedItemSerializer(data=entry)

    assert serializer.is_valid(raise_exception=True) is True

    serializer.save(channel, copyright="test something")
    upload.refresh_from_db()

    assert upload.track == track
    assert upload.library == channel.library
    assert upload.import_status == "finished"
    assert upload.source == "https://file.domain/audio.mp3"
    assert upload.size == 54315884
    assert upload.duration == 1357
    assert upload.mimetype == "audio/mpeg"
    assert upload.track.uuid == expected_uuid
    assert upload.track.artist == channel.artist
    assert upload.track.copyright == "test something"
    assert upload.track.position == 33
    assert upload.track.disc_number == 2
    assert upload.track.creation_date == datetime.datetime(2020, 3, 11, 16).replace(
        tzinfo=pytz.utc
    )
    assert upload.track.get_tags() == ["pop", "rock"]
    assert upload.track.attachment_cover.url == "https://image.url/"
    assert upload.track.description.text == "<p>Html content</p>"
    assert upload.track.description.content_type == "text/html"


def test_get_channel_from_rss_url(db, r_mock, mocker):
    rss_url = "http://example.rss/"
    xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Hello</title>
                <description>Description</description>
                <link>http://public.url</link>
                <atom:link rel="self" type="application/rss+xml" href="http://real.rss.url"/>
                <lastBuildDate>Wed, 11 Mar 2020 16:01:08 GMT</lastBuildDate>
                <pubDate>Wed, 11 Mar 2020 16:00:00 GMT</pubDate>
                <ttl>30</ttl>
                <language>en</language>
                <copyright>2019 Tests</copyright>
                <itunes:keywords>pop rock</itunes:keywords>
                <image>
                    <url>
                        https://image.url
                    </url>
                    <title>Image caption</title>
                </image>
                <itunes:image href="https://image.url"/>
                <itunes:subtitle>Subtitle</itunes:subtitle>
                <itunes:type>episodic</itunes:type>
                <itunes:author>Author</itunes:author>
                <itunes:summary><![CDATA[Some content]]></itunes:summary>
                <itunes:owner>
                    <itunes:name>Name</itunes:name>
                    <itunes:email>email@domain</itunes:email>
                </itunes:owner>
                <itunes:explicit>yes</itunes:explicit>
                <itunes:keywords/>
                <itunes:category text="Business">
                    <itunes:category text="Entrepreneurship">
                </itunes:category>
                <item>
                    <title>Episode 33</title>
                    <itunes:subtitle>Subtitle</itunes:subtitle>
                    <itunes:summary><![CDATA[<p>Html content</p>]]></itunes:summary>
                    <guid isPermaLink="false"><![CDATA[16f66fff-41ae-4a1c-9101-2746218c4f32]]></guid>
                    <pubDate>Wed, 11 Mar 2020 18:00:00 GMT</pubDate>
                    <itunes:duration>00:22:37</itunes:duration>
                    <itunes:keywords>pop rock</itunes:keywords>
                    <itunes:season>2</itunes:season>
                    <itunes:episode>33</itunes:episode>
                    <itunes:image href="https://image.url/" />
                    <description><![CDATA[Html content]]></description>
                    <link>http://public.url/</link>
                    <enclosure url="https://file.domain/audio.mp3" length="54315884" type="audio/mpeg"/>
                </item>
                <item>
                    <title>Episode 32</title>
                    <itunes:subtitle>Subtitle</itunes:subtitle>
                    <itunes:summary><![CDATA[<p>Html content</p>]]></itunes:summary>
                    <guid isPermaLink="false"><![CDATA[16f66fff-41ae-4a1c-910e-2746218c4f32]]></guid>
                    <pubDate>Wed, 11 Mar 2020 17:00:00 GMT</pubDate>
                    <itunes:duration>00:22:37</itunes:duration>
                    <itunes:keywords>pop rock</itunes:keywords>
                    <itunes:season>2</itunes:season>
                    <itunes:episode>32</itunes:episode>
                    <itunes:image href="https://image.url/" />
                    <description><![CDATA[Html content]]></description>
                    <link>http://public.url/</link>
                    <enclosure url="https://file.domain/audio2.mp3" length="54315884" type="audio/mpeg"/>
                </item>
                <item>
                    <title>Ignored, missing enĉlosure</title>
                    <itunes:subtitle>Subtitle</itunes:subtitle>
                    <itunes:summary><![CDATA[<p>Html content</p>]]></itunes:summary>
                    <guid isPermaLink="false"><![CDATA[16f66fff-41ae-4a1c-910e-2746218c4f32]]></guid>
                    <pubDate>Wed, 11 Mar 2020 16:00:00 GMT</pubDate>
                    <itunes:duration>00:22:37</itunes:duration>
                    <itunes:keywords>pop rock</itunes:keywords>
                    <itunes:season>2</itunes:season>
                    <itunes:episode>32</itunes:episode>
                    <itunes:image href="https://image.url/" />
                    <description><![CDATA[Html content]]></description>
                    <link>http://public.url/</link>
                </item>
            </channel>
        </rss>
    """
    parsed_feed = feedparser.parse(xml_payload)
    r_mock.get(rss_url, text=xml_payload)

    update_modification_date = mocker.spy(common_utils, "update_modification_date")
    feed_init = mocker.spy(serializers.RssFeedSerializer, "__init__")
    feed_save = mocker.spy(serializers.RssFeedSerializer, "save")
    item_init = mocker.spy(serializers.RssFeedItemSerializer, "__init__")
    item_save = mocker.spy(serializers.RssFeedItemSerializer, "save")
    on_commit = mocker.spy(common_utils, "on_commit")
    channel, uploads = serializers.get_channel_from_rss_url(rss_url)

    assert channel.artist.name == "Hello"

    serializer_instance = feed_init.call_args[0][0]
    feed_init.assert_called_once_with(serializer_instance, data=parsed_feed.feed)
    feed_save.assert_called_once_with(serializer_instance, rss_url)

    for i in [0, 1]:
        serializer_instance = item_init.call_args_list[i][0][0]
        item_init.assert_any_call(serializer_instance, data=parsed_feed.entries[i])
        item_save.assert_any_call(
            serializer_instance, channel, existing_uploads=[], copyright="2019 Tests"
        )

    assert len(uploads) == 2
    assert channel.library.uploads.count() == 2

    on_commit.assert_any_call(
        serializers.music_models.TrackActor.create_entries,
        library=channel.library,
        delete_existing=True,
    )
    update_modification_date.assert_called_once_with(
        channel.artist, date=uploads[0].track.creation_date
    )


def test_get_channel_from_rss_honor_mrf_inbox_before_http(
    mrf_inbox_registry, factories, mocker
):
    apply = mocker.patch.object(mrf_inbox_registry, "apply", return_value=(None, False))
    rss_url = "https://rss.domain/test"

    with pytest.raises(serializers.FeedFetchException, match=r".*blocked.*"):
        serializers.get_channel_from_rss_url(rss_url)

    apply.assert_any_call({"id": rss_url})


def test_get_channel_from_rss_honor_mrf_inbox_after_http(
    mrf_inbox_registry, r_mock, mocker, db
):
    apply = mocker.patch.object(
        mrf_inbox_registry,
        "apply",
        side_effect=[(True, False), (True, False), (None, False)],
    )
    rss_url = "https://rss.domain/test"
    # the feed has a redirection, we check both urls
    final_rss_url = "https://real.rss.domain/test"
    public_url = "http://public.url"
    xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Hello</title>
                <description>Description</description>
                <link>{}</link>
                <atom:link rel="self" type="application/rss+xml" href="{}"/>
                <language>en</language>
                <copyright>2019 Tests</copyright>
                <itunes:keywords>pop rock</itunes:keywords>
            </channel>
        </rss>
    """.format(
        public_url, final_rss_url
    )

    r_mock.get(rss_url, text=xml_payload)

    with pytest.raises(serializers.FeedFetchException, match=r".*blocked.*"):
        serializers.get_channel_from_rss_url(rss_url)

    apply.assert_any_call({"id": rss_url})
    apply.assert_any_call({"id": final_rss_url})
    apply.assert_any_call({"id": public_url})


def test_opml_serializer(factories, now):
    channels = [
        factories["audio.Channel"](),
        factories["audio.Channel"](),
        factories["audio.Channel"](),
    ]

    title = "Hello world"
    expected = {
        "version": "2.0",
        "head": [
            {
                "date": [{"value": serializers.rfc822_date(now)}],
                "title": [{"value": title}],
            }
        ],
        "body": [
            {
                "outline": [
                    serializers.get_opml_outline(channels[0]),
                    serializers.get_opml_outline(channels[1]),
                    serializers.get_opml_outline(channels[2]),
                ],
            }
        ],
    }

    assert serializers.get_opml(channels=channels, date=now, title=title) == expected


def test_opml_outline_serializer(factories, now):
    channel = factories["audio.Channel"]()

    expected = {
        "title": channel.artist.name,
        "text": channel.artist.name,
        "type": "rss",
        "xmlUrl": channel.get_rss_url(),
        "htmlUrl": channel.actor.url,
    }

    assert serializers.get_opml_outline(channel) == expected

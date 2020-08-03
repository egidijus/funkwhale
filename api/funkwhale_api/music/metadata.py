import base64
from collections.abc import Mapping
import datetime
import logging
import arrow

import mutagen._util
import mutagen.oggtheora
import mutagen.oggvorbis
import mutagen.flac

from rest_framework import serializers

from funkwhale_api.tags import models as tags_models

logger = logging.getLogger(__name__)
NODEFAULT = object()
# default title used when imported tracks miss the `Album` tag, see #122
UNKNOWN_ALBUM = "[Unknown Album]"


class TagNotFound(KeyError):
    pass


class UnsupportedTag(KeyError):
    pass


class ParseError(ValueError):
    pass


def get_id3_tag(f, k):
    if k == "pictures":
        return f.tags.getall("APIC")
    # First we try to grab the standard key
    possible_attributes = [("text", True), ("url", False)]
    for attr, select_first in possible_attributes:
        try:
            v = getattr(f.tags[k], attr)
            if select_first:
                v = v[0]
            return v
        except KeyError:
            break
        except IndexError:
            break
        except AttributeError:
            continue

    # then we fallback on parsing non standard tags
    all_tags = f.tags.getall("TXXX")
    try:
        matches = [t for t in all_tags if t.desc.lower() == k.lower()]
        return matches[0].text[0]
    except (KeyError, IndexError):
        raise TagNotFound(k)


def clean_id3_pictures(apic):
    pictures = []
    for p in list(apic):
        pictures.append(
            {
                "mimetype": p.mime,
                "content": p.data,
                "description": p.desc,
                "type": p.type.real,
            }
        )
    return pictures


def get_mp4_tag(f, k):
    if k == "pictures":
        return f.get("covr", [])
    raw_value = f.get(k, None)

    if not raw_value:
        raise TagNotFound(k)

    value = raw_value[0]
    try:
        return value.decode()
    except AttributeError:
        return value


def get_mp4_position(raw_value):
    return raw_value[0]


def clean_mp4_pictures(raw_pictures):
    pictures = []
    for p in list(raw_pictures):
        if p.imageformat == p.FORMAT_JPEG:
            mimetype = "image/jpeg"
        elif p.imageformat == p.FORMAT_PNG:
            mimetype = "image/png"
        else:
            continue
        pictures.append(
            {
                "mimetype": mimetype,
                "content": bytes(p),
                "description": "",
                "type": mutagen.id3.PictureType.COVER_FRONT,
            }
        )
    return pictures


def get_flac_tag(f, k):
    if k == "pictures":
        return f.pictures
    try:
        return f.get(k, [])[0]
    except (KeyError, IndexError):
        raise TagNotFound(k)


def clean_flac_pictures(apic):
    pictures = []
    for p in list(apic):
        pictures.append(
            {
                "mimetype": p.mime,
                "content": p.data,
                "description": p.desc,
                "type": p.type.real,
            }
        )
    return pictures


def clean_ogg_pictures(metadata_block_picture):
    pictures = []
    for b64_data in [metadata_block_picture]:

        try:
            data = base64.b64decode(b64_data)
        except (TypeError, ValueError):
            continue

        try:
            picture = mutagen.flac.Picture(data)
        except mutagen.flac.FLACError:
            continue

        pictures.append(
            {
                "mimetype": picture.mime,
                "content": picture.data,
                "description": "",
                "type": picture.type.real,
            }
        )
    return pictures


def get_mp3_recording_id(f, k):
    try:
        return [t for t in f.tags.getall("UFID") if "musicbrainz.org" in t.owner][
            0
        ].data.decode("utf-8")
    except IndexError:
        raise TagNotFound(k)


def get_mp3_comment(f, k):
    keys_to_try = ["COMM", "COMM::eng"]
    for key in keys_to_try:
        try:
            return get_id3_tag(f, key)
        except TagNotFound:
            pass

    raise TagNotFound("COMM")


VALIDATION = {}

CONF = {
    "OggOpus": {
        "getter": lambda f, k: f[k][0],
        "fields": {
            "position": {"field": "TRACKNUMBER"},
            "disc_number": {"field": "DISCNUMBER"},
            "title": {},
            "artist": {},
            "artists": {},
            "album_artist": {"field": "albumartist"},
            "album": {},
            "date": {"field": "date"},
            "musicbrainz_albumid": {},
            "musicbrainz_artistid": {},
            "musicbrainz_albumartistid": {},
            "mbid": {"field": "musicbrainz_trackid"},
            "license": {},
            "copyright": {},
            "genre": {},
            "pictures": {
                "field": "metadata_block_picture",
                "to_application": clean_ogg_pictures,
            },
            "comment": {"field": "comment"},
        },
    },
    "OggVorbis": {
        "getter": lambda f, k: f[k][0],
        "fields": {
            "position": {"field": "TRACKNUMBER"},
            "disc_number": {"field": "DISCNUMBER"},
            "title": {},
            "artist": {},
            "artists": {},
            "album_artist": {"field": "albumartist"},
            "album": {},
            "date": {"field": "date"},
            "musicbrainz_albumid": {},
            "musicbrainz_artistid": {},
            "musicbrainz_albumartistid": {},
            "mbid": {"field": "musicbrainz_trackid"},
            "license": {},
            "copyright": {},
            "genre": {},
            "pictures": {
                "field": "metadata_block_picture",
                "to_application": clean_ogg_pictures,
            },
            "comment": {"field": "comment"},
        },
    },
    "OggTheora": {
        "getter": lambda f, k: f[k][0],
        "fields": {
            "position": {"field": "TRACKNUMBER"},
            "disc_number": {"field": "DISCNUMBER"},
            "title": {},
            "artist": {},
            "artists": {},
            "album_artist": {"field": "albumartist"},
            "album": {},
            "date": {"field": "date"},
            "musicbrainz_albumid": {"field": "MusicBrainz Album Id"},
            "musicbrainz_artistid": {"field": "MusicBrainz Artist Id"},
            "musicbrainz_albumartistid": {"field": "MusicBrainz Album Artist Id"},
            "mbid": {"field": "MusicBrainz Track Id"},
            "license": {},
            "copyright": {},
            "genre": {},
            "comment": {"field": "comment"},
        },
    },
    "MP3": {
        "getter": get_id3_tag,
        "clean_pictures": clean_id3_pictures,
        "fields": {
            "position": {"field": "TRCK"},
            "disc_number": {"field": "TPOS"},
            "title": {"field": "TIT2"},
            "artist": {"field": "TPE1"},
            "artists": {"field": "ARTISTS"},
            "album_artist": {"field": "TPE2"},
            "album": {"field": "TALB"},
            "date": {"field": "TDRC"},
            "musicbrainz_albumid": {"field": "MusicBrainz Album Id"},
            "musicbrainz_artistid": {"field": "MusicBrainz Artist Id"},
            "genre": {"field": "TCON"},
            "musicbrainz_albumartistid": {"field": "MusicBrainz Album Artist Id"},
            "mbid": {"field": "UFID", "getter": get_mp3_recording_id},
            "pictures": {},
            "license": {"field": "WCOP"},
            "copyright": {"field": "TCOP"},
            "comment": {"field": "COMM", "getter": get_mp3_comment},
        },
    },
    "MP4": {
        "getter": get_mp4_tag,
        "clean_pictures": clean_mp4_pictures,
        "fields": {
            "position": {"field": "trkn", "to_application": get_mp4_position},
            "disc_number": {"field": "disk", "to_application": get_mp4_position},
            "title": {"field": "©nam"},
            "artist": {"field": "©ART"},
            "artists": {"field": "----:com.apple.iTunes:ARTISTS"},
            "album_artist": {"field": "aART"},
            "album": {"field": "©alb"},
            "date": {"field": "©day"},
            "musicbrainz_albumid": {
                "field": "----:com.apple.iTunes:MusicBrainz Album Id"
            },
            "musicbrainz_artistid": {
                "field": "----:com.apple.iTunes:MusicBrainz Artist Id"
            },
            "genre": {"field": "©gen"},
            "musicbrainz_albumartistid": {
                "field": "----:com.apple.iTunes:MusicBrainz Album Artist Id"
            },
            "mbid": {"field": "----:com.apple.iTunes:MusicBrainz Track Id"},
            "pictures": {},
            "license": {"field": "----:com.apple.iTunes:LICENSE"},
            "copyright": {"field": "cprt"},
            "comment": {"field": "©cmt"},
        },
    },
    "FLAC": {
        "getter": get_flac_tag,
        "clean_pictures": clean_flac_pictures,
        "fields": {
            "position": {"field": "tracknumber"},
            "disc_number": {"field": "discnumber"},
            "title": {},
            "artist": {},
            "artists": {},
            "album_artist": {"field": "albumartist"},
            "album": {},
            "date": {"field": "date"},
            "musicbrainz_albumid": {},
            "musicbrainz_artistid": {},
            "musicbrainz_albumartistid": {},
            "genre": {},
            "mbid": {"field": "musicbrainz_trackid"},
            "test": {},
            "pictures": {},
            "license": {},
            "copyright": {},
            "comment": {},
        },
    },
}

ALL_FIELDS = [
    "position",
    "disc_number",
    "title",
    "artist",
    "album_artist",
    "album",
    "date",
    "musicbrainz_albumid",
    "musicbrainz_artistid",
    "musicbrainz_albumartistid",
    "mbid",
    "license",
    "copyright",
    "comment",
]


class Metadata(Mapping):
    def __init__(self, filething, kind=mutagen.File):
        self._file = kind(filething)
        if self._file is None:
            raise ValueError("Cannot parse metadata from {}".format(filething))
        self.fallback = self.load_fallback(filething, self._file)
        ft = self.get_file_type(self._file)
        try:
            self._conf = CONF[ft]
        except KeyError:
            raise ValueError("Unsupported format {}".format(ft))

    def get_file_type(self, f):
        return f.__class__.__name__

    def load_fallback(self, filething, parent):
        """
        In some situations, such as Ogg Theora files tagged with MusicBrainz Picard,
        part of the tags are only available in the ogg vorbis comments
        """
        try:
            filething.seek(0)
        except AttributeError:
            pass
        if isinstance(parent, mutagen.oggtheora.OggTheora):
            try:
                return Metadata(filething, kind=mutagen.oggvorbis.OggVorbis)
            except (ValueError, mutagen._util.MutagenError):
                raise
                pass

    def get(self, key, default=NODEFAULT):
        try:
            return self._get_from_self(key)
        except TagNotFound:
            if not self.fallback:
                if default != NODEFAULT:
                    return default
                else:
                    raise
            else:
                return self.fallback.get(key, default=default)
        except UnsupportedTag:
            if not self.fallback:
                raise
            else:
                return self.fallback.get(key, default=default)

    def all(self):
        """
        Return a dict with all support metadata fields, if they are available
        """
        final = {}
        for field in self._conf["fields"]:
            if field in ["pictures"]:
                continue
            value = self.get(field, None)
            if value is None:
                continue
            final[field] = str(value)

        return final

    def _get_from_self(self, key, default=NODEFAULT):
        try:
            field_conf = self._conf["fields"][key]
        except KeyError:
            raise UnsupportedTag("{} is not supported for this file format".format(key))
        real_key = field_conf.get("field", key)
        try:
            getter = field_conf.get("getter", self._conf["getter"])
            v = getter(self._file, real_key)
        except KeyError:
            if default == NODEFAULT:
                raise TagNotFound(real_key)
            return default

        converter = field_conf.get("to_application")
        if converter:
            v = converter(v)
        field = VALIDATION.get(key)
        if field:
            v = field.to_python(v)
        return v

    def get_picture(self, *picture_types):
        if not picture_types:
            raise ValueError("You need to request at least one picture type")
        ptypes = [
            getattr(mutagen.id3.PictureType, picture_type.upper())
            for picture_type in picture_types
        ]

        try:
            pictures = self.get("pictures")
        except (UnsupportedTag, TagNotFound):
            return

        cleaner = self._conf.get("clean_pictures", lambda v: v)
        pictures = cleaner(pictures)
        if not pictures:
            return
        for ptype in ptypes:
            for p in pictures:
                if p["type"] == ptype:
                    return p

    def __getitem__(self, key):
        return self.get(key)

    def __len__(self):
        return 1

    def __iter__(self):
        for field in self._conf["fields"]:
            yield field


class ArtistField(serializers.Field):
    def __init__(self, *args, **kwargs):
        self.for_album = kwargs.pop("for_album", False)
        super().__init__(*args, **kwargs)

    def get_value(self, data):
        if self.for_album:
            keys = [
                ("artists", "artists"),
                ("names", "album_artist"),
                ("mbids", "musicbrainz_albumartistid"),
            ]
        else:
            keys = [
                ("artists", "artists"),
                ("names", "artist"),
                ("mbids", "musicbrainz_artistid"),
            ]

        final = {}
        for field, key in keys:
            final[field] = data.get(key, None)

        return final

    def to_internal_value(self, data):
        # we have multiple values that can be separated by various separators
        separators = [";", ","]
        # we get a list like that if tagged via musicbrainz
        # ae29aae4-abfb-4609-8f54-417b1f4d64cc; 3237b5a8-ae44-400c-aa6d-cea51f0b9074;
        raw_mbids = data["mbids"]
        used_separator = None
        mbids = [raw_mbids]
        if raw_mbids:
            if "/" in raw_mbids:
                # it's a featuring, we can't handle this now
                mbids = []
            else:
                for separator in separators:
                    if separator in raw_mbids:
                        used_separator = separator
                        mbids = [m.strip() for m in raw_mbids.split(separator)]
                        break

        # now, we split on artist names, using the same separator as the one used
        # by mbids, if any
        names = []

        if data.get("artists", None):
            for separator in separators:
                if separator in data["artists"]:
                    names = [n.strip() for n in data["artists"].split(separator)]
                    break
            if not names:
                names = [data["artists"]]
        elif used_separator and mbids:
            names = [n.strip() for n in data["names"].split(used_separator)]
        else:
            names = [data["names"]]

        final = []
        for i, name in enumerate(names):
            try:
                mbid = mbids[i]
            except IndexError:
                mbid = None
            artist = {"name": name, "mbid": mbid}
            final.append(artist)
        field = serializers.ListField(
            child=ArtistSerializer(strict=self.context.get("strict", True)),
            min_length=1,
        )
        return field.to_internal_value(final)


class AlbumField(serializers.Field):
    def get_value(self, data):
        return data

    def to_internal_value(self, data):
        try:
            title = data.get("album") or ""
        except TagNotFound:
            title = ""

        title = title.strip() or UNKNOWN_ALBUM
        final = {
            "title": title,
            "release_date": data.get("date", None),
            "mbid": data.get("musicbrainz_albumid", None),
        }
        artists_field = ArtistField(for_album=True)
        payload = artists_field.get_value(data)
        try:
            artists = artists_field.to_internal_value(payload)
        except serializers.ValidationError as e:
            artists = []
            logger.debug("Ignoring validation error on album artists: %s", e)
        album_serializer = AlbumSerializer(data=final)
        album_serializer.is_valid(raise_exception=True)
        album_serializer.validated_data["artists"] = artists
        return album_serializer.validated_data


class CoverDataField(serializers.Field):
    def get_value(self, data):
        return data

    def to_internal_value(self, data):
        return data.get_picture("cover_front", "other")


class PermissiveDateField(serializers.CharField):
    def to_internal_value(self, value):
        if not value:
            return None
        value = super().to_internal_value(str(value))
        ADDITIONAL_FORMATS = [
            "%Y-%d-%m %H:%M",  # deezer date format
            "%Y-%W",  # weird date format based on week number, see #718
        ]

        for date_format in ADDITIONAL_FORMATS:
            try:
                parsed = datetime.datetime.strptime(value, date_format)
            except ValueError:
                continue
            else:
                return datetime.date(parsed.year, parsed.month, parsed.day)

        try:
            parsed = arrow.get(str(value))
            return datetime.date(parsed.year, parsed.month, parsed.day)
        except (arrow.parser.ParserError, ValueError):
            pass

        return None


def extract_tags_from_genre(string):
    tags = []
    delimiter = "@@@@@"
    for d in [" - ", ",", ";", "/"]:
        # Replace common tags separators by a custom delimiter
        string = string.replace(d, delimiter)

    # loop on the parts (splitting on our custom delimiter)
    for tag in string.split(delimiter):
        tag = tag.strip()
        for d in ["-"]:
            # preparation for replacement so that Pop-Rock becomes Pop Rock, then PopRock
            # (step 1, step 2 happens below)
            tag = tag.replace(d, " ")
        if not tag:
            continue
        final_tag = ""
        if not tags_models.TAG_REGEX.match(tag.replace(" ", "")):
            # the string contains some non words chars ($, €, etc.), right now
            # we simply skip such tags
            continue
        # concatenate the parts and uppercase them so that 'pop rock' becomes 'PopRock'
        if len(tag.split(" ")) == 1:
            # we append the tag "as is", because it doesn't contain any space
            tags.append(tag)
            continue
        for part in tag.split(" "):
            # the tag contains space, there's work to do to have consistent case
            # 'pop rock' -> 'PopRock'
            # (step 2)
            if not part:
                continue
            final_tag += part[0].upper() + part[1:]
        if final_tag:
            tags.append(final_tag)
    return tags


class TagsField(serializers.CharField):
    def get_value(self, data):
        return data

    def to_internal_value(self, data):
        try:
            value = data.get("genre") or ""
        except TagNotFound:
            return []
        value = super().to_internal_value(str(value))

        return extract_tags_from_genre(value)


class MBIDField(serializers.UUIDField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("allow_null", True)
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)

    def to_internal_value(self, v):
        if v in ["", None]:
            return None
        return super().to_internal_value(v)


class ArtistSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    mbid = MBIDField()

    def __init__(self, *args, **kwargs):
        self.strict = kwargs.pop("strict", True)
        super().__init__(*args, **kwargs)

    def validate_name(self, v):
        if self.strict and not v:
            raise serializers.ValidationError("This field is required.")
        return v


class AlbumSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_null=True)
    mbid = MBIDField()
    release_date = PermissiveDateField(
        required=False, allow_null=True, allow_blank=True
    )

    def validate_title(self, v):
        if self.context.get("strict", True) and not v:
            raise serializers.ValidationError("This field is required.")
        return v


class PositionField(serializers.CharField):
    def to_internal_value(self, v):
        v = super().to_internal_value(v)
        if not v:
            return v

        try:
            return int(v)
        except ValueError:
            # maybe the position is of the form "1/4"
            pass

        try:
            return int(v.split("/")[0])
        except (ValueError, AttributeError, IndexError):
            pass


class DescriptionField(serializers.CharField):
    def get_value(self, data):
        return data

    def to_internal_value(self, data):
        try:
            value = data.get("comment") or None
        except TagNotFound:
            return None
        if not value:
            return None
        value = super().to_internal_value(value)
        return {"text": value, "content_type": "text/plain"}


class TrackMetadataSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_null=True)
    position = PositionField(allow_blank=True, allow_null=True, required=False)
    disc_number = PositionField(allow_blank=True, allow_null=True, required=False)
    copyright = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    license = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    mbid = MBIDField()
    tags = TagsField(allow_blank=True, allow_null=True, required=False)
    description = DescriptionField(allow_null=True, allow_blank=True, required=False)

    album = AlbumField()
    artists = ArtistField()
    cover_data = CoverDataField()

    remove_blank_null_fields = [
        "copyright",
        "description",
        "license",
        "position",
        "disc_number",
        "mbid",
        "tags",
    ]

    def validate_title(self, v):
        if self.context.get("strict", True) and not v:
            raise serializers.ValidationError("This field is required.")
        return v

    def validate(self, validated_data):
        validated_data = super().validate(validated_data)
        for field in self.remove_blank_null_fields:
            try:
                v = validated_data[field]
            except KeyError:
                continue
            if v in ["", None, []]:
                validated_data.pop(field)
        validated_data["album"]["cover_data"] = validated_data.pop("cover_data", None)
        return validated_data


class FakeMetadata(Mapping):
    def __init__(self, data, picture=None):
        self.data = data
        self.picture = None

    def __getitem__(self, key):
        return self.data[key]

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        yield from self.data

    def get_picture(self, *args):
        return self.picture

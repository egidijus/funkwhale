import logging
import re

from django.db import transaction

from . import models

logger = logging.getLogger(__name__)

MODEL_FIELDS = [
    "redistribute",
    "derivative",
    "attribution",
    "copyleft",
    "commercial",
    "url",
]


@transaction.atomic
def load(data):
    """
    Load/update database objects with our hardcoded data
    """
    existing = models.License.objects.all()
    existing_by_code = {e.code: e for e in existing}
    to_create = []

    for row in data:
        try:
            license = existing_by_code[row["code"]]
        except KeyError:
            logger.debug("Loading new license: {}".format(row["code"]))
            to_create.append(
                models.License(code=row["code"], **{f: row[f] for f in MODEL_FIELDS})
            )
        else:
            logger.debug("Updating license: {}".format(row["code"]))
            stored = [getattr(license, f) for f in MODEL_FIELDS]
            wanted = [row[f] for f in MODEL_FIELDS]
            if wanted == stored:
                continue
            # the object in database needs an update
            for f in MODEL_FIELDS:
                setattr(license, f, row[f])

            license.save()

    models.License.objects.bulk_create(to_create)
    return sorted(models.License.objects.all(), key=lambda o: o.code)


_cache = None


def match(*values):
    """
    Given a string, extracted from music file tags, return corresponding License
    instance, if found
    """
    global _cache
    for value in values:
        if not value:
            continue

        # we are looking for the first url in our value
        # This regex is not perfect, but it's good enough for now
        urls = re.findall(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
            value,
        )
        if not urls:
            logger.debug('Impossible to guess license from string "{}"'.format(value))
            continue
        url = urls[0]
        if _cache:
            existing = _cache
        else:
            existing = load(LICENSES)
            _cache = existing
        for license in existing:
            if license.conf is None:
                continue
            for i in license.conf["identifiers"]:
                if match_urls(url, i):
                    return license


def match_urls(*urls):
    """
    We want to ensure the two url match but don't care for protocol
    or trailing slashes
    """
    urls = [u.rstrip("/") for u in urls]
    urls = [u.lstrip("http://") for u in urls]
    urls = [u.lstrip("https://") for u in urls]
    return len(set(urls)) == 1


def get_cc_license(version, perks, country=None, country_name=None):
    if len(perks) == 0:
        raise ValueError("No perks!")

    url_template = "//creativecommons.org/licenses/{type}/{version}/"

    code_parts = []
    name_parts = []
    perks_data = [
        ("by", "Attribution"),
        ("nc", "NonCommercial"),
        ("sa", "ShareAlike"),
        ("nd", "NoDerivatives"),
    ]
    for perk, name in perks_data:
        if perk in perks:
            code_parts.append(perk)
            name_parts.append(name)
    url = url_template.format(version=version, type="-".join(code_parts))
    code_parts.append(version)
    name = "Creative commons - {perks} {version}".format(
        perks="-".join(name_parts), version=version
    )
    if country:
        code_parts.append(country)
        name += " {}".format(country_name)
        url += country + "/"
    data = {
        "name": name,
        "code": "cc-{}".format("-".join(code_parts)),
        "redistribute": True,
        "commercial": "nc" not in perks,
        "derivative": "nd" not in perks,
        "copyleft": "sa" in perks,
        "attribution": "by" in perks,
        "url": "https:" + url,
        "identifiers": ["http:" + url],
    }

    return data


COUNTRIES = {
    "ar": "Argentina",
    "au": "Australia",
    "at": "Austria",
    "be": "Belgium",
    "br": "Brazil",
    "bg": "Bulgaria",
    "ca": "Canada",
    "cl": "Chile",
    "cn": "China Mainland",
    "co": "Colombia",
    "cr": "Costa Rica",
    "hr": "Croatia",
    "cz": "Czech Republic",
    "dk": "Denmark",
    "ec": "Ecuador",
    "eg": "Egypt",
    "ee": "Estonia",
    "fi": "Finland",
    "fr": "France",
    "de": "Germany",
    "gr": "Greece",
    "gt": "Guatemala",
    "hk": "Hong Kong",
    "hu": "Hungary",
    "igo": "IGO",
    "in": "India",
    "ie": "Ireland",
    "il": "Israel",
    "it": "Italy",
    "jp": "Japan",
    "lu": "Luxembourg",
    "mk": "Macedonia",
    "my": "Malaysia",
    "mt": "Malta",
    "mx": "Mexico",
    "nl": "Netherlands",
    "nz": "New Zealand",
    "no": "Norway",
    "pe": "Peru",
    "ph": "Philippines",
    "pl": "Poland",
    "pt": "Portugal",
    "pr": "Puerto Rico",
    "ro": "Romania",
    "rs": "Serbia",
    "sg": "Singapore",
    "si": "Slovenia",
    "za": "South Africa",
    "kr": "South Korea",
    "es": "Spain",
    "se": "Sweden",
    "ch": "Switzerland",
    "tw": "Taiwan",
    "th": "Thailand",
    "uk": "UK: England &amp; Wales",
    "scotland": "UK: Scotland",
    "ug": "Uganda",
    "us": "United States",
    "ve": "Venezuela",
    "vn": "Vietnam",
}
CC_30_COUNTRIES = [
    "at",
    "au",
    "br",
    "ch",
    "cl",
    "cn",
    "cr",
    "cz",
    "de",
    "ec",
    "ee",
    "eg",
    "es",
    "fr",
    "gr",
    "gt",
    "hk",
    "hr",
    "ie",
    "igo",
    "it",
    "lu",
    "nl",
    "no",
    "nz",
    "ph",
    "pl",
    "pr",
    "pt",
    "ro",
    "rs",
    "sg",
    "th",
    "tw",
    "ug",
    "us",
    "ve",
    "vn",
    "za",
]

CC_25_COUNTRIES = [
    "ar",
    "bg",
    "ca",
    "co",
    "dk",
    "hu",
    "il",
    "in",
    "mk",
    "mt",
    "mx",
    "my",
    "pe",
    "scotland",
]

LICENSES = [
    # a non-exhaustive list: http://musique-libre.org/doc/le-tableau-des-licences-libres-et-ouvertes-de-dogmazic/
    {
        "code": "cc0-1.0",
        "name": "CC0 - Public domain",
        "redistribute": True,
        "derivative": True,
        "commercial": True,
        "attribution": False,
        "copyleft": False,
        "url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "identifiers": [
            # note the http here.
            # This is the kind of URL that is embedded in music files metadata
            "http://creativecommons.org/publicdomain/zero/1.0/"
        ],
    },
    {
        "code": "LAL-1.3",
        "name": "Licence Art Libre 1.3",
        "redistribute": True,
        "derivative": True,
        "commercial": True,
        "attribution": True,
        "copyleft": True,
        "url": "https://artlibre.org/licence/lal",
        "identifiers": ["http://artlibre.org/licence/lal"],
    },
    # Creative commons version 4.0
    get_cc_license(version="4.0", perks=["by"]),
    get_cc_license(version="4.0", perks=["by", "sa"]),
    get_cc_license(version="4.0", perks=["by", "nc"]),
    get_cc_license(version="4.0", perks=["by", "nc", "sa"]),
    get_cc_license(version="4.0", perks=["by", "nc", "nd"]),
    get_cc_license(version="4.0", perks=["by", "nd"]),
    # Creative commons version 3.0
    get_cc_license(version="3.0", perks=["by"]),
    get_cc_license(version="3.0", perks=["by", "sa"]),
    get_cc_license(version="3.0", perks=["by", "nc"]),
    get_cc_license(version="3.0", perks=["by", "nc", "sa"]),
    get_cc_license(version="3.0", perks=["by", "nc", "nd"]),
    get_cc_license(version="3.0", perks=["by", "nd"]),
    # Creative commons version 2.5
    get_cc_license(version="2.5", perks=["by"]),
    get_cc_license(version="2.5", perks=["by", "sa"]),
    get_cc_license(version="2.5", perks=["by", "nc"]),
    get_cc_license(version="2.5", perks=["by", "nc", "sa"]),
    get_cc_license(version="2.5", perks=["by", "nc", "nd"]),
    get_cc_license(version="2.5", perks=["by", "nd"]),
    # Creative commons version 2.0
    get_cc_license(version="2.0", perks=["by"]),
    get_cc_license(version="2.0", perks=["by", "sa"]),
    get_cc_license(version="2.0", perks=["by", "nc"]),
    get_cc_license(version="2.0", perks=["by", "nc", "sa"]),
    get_cc_license(version="2.0", perks=["by", "nc", "nd"]),
    get_cc_license(version="2.0", perks=["by", "nd"]),
    # Creative commons version 1.0
    get_cc_license(version="1.0", perks=["by"]),
    get_cc_license(version="1.0", perks=["by", "sa"]),
    get_cc_license(version="1.0", perks=["by", "nc"]),
    get_cc_license(version="1.0", perks=["by", "nc", "sa"]),
    get_cc_license(version="1.0", perks=["by", "nc", "nd"]),
    get_cc_license(version="1.0", perks=["by", "nd"]),
]

# generate ported (by country) CC licenses:

for country in CC_30_COUNTRIES:
    name = COUNTRIES[country]
    LICENSES += [
        get_cc_license(version="3.0", perks=["by"], country=country, country_name=name),
        get_cc_license(
            version="3.0", perks=["by", "sa"], country=country, country_name=name
        ),
        get_cc_license(
            version="3.0", perks=["by", "nc"], country=country, country_name=name
        ),
        get_cc_license(
            version="3.0", perks=["by", "nc", "sa"], country=country, country_name=name
        ),
        get_cc_license(
            version="3.0", perks=["by", "nc", "nd"], country=country, country_name=name
        ),
        get_cc_license(
            version="3.0", perks=["by", "nd"], country=country, country_name=name
        ),
    ]


for country in CC_25_COUNTRIES:
    name = COUNTRIES[country]
    LICENSES += [
        get_cc_license(version="2.5", perks=["by"], country=country, country_name=name),
        get_cc_license(
            version="2.5", perks=["by", "sa"], country=country, country_name=name
        ),
        get_cc_license(
            version="2.5", perks=["by", "nc"], country=country, country_name=name
        ),
        get_cc_license(
            version="2.5", perks=["by", "nc", "sa"], country=country, country_name=name
        ),
        get_cc_license(
            version="2.5", perks=["by", "nc", "nd"], country=country, country_name=name
        ),
        get_cc_license(
            version="2.5", perks=["by", "nd"], country=country, country_name=name
        ),
    ]

LICENSES = sorted(LICENSES, key=lambda l: l["code"])
LICENSES_BY_ID = {l["code"]: l for l in LICENSES}

import unicodedata
import re
from django.conf import settings
from django.db.models import Q

from funkwhale_api.common import session
from funkwhale_api.moderation import mrf

from . import exceptions
from . import signing


def full_url(path):
    """
    Given a relative path, return a full url usable for federation purpose
    """
    if path.startswith("http://") or path.startswith("https://"):
        return path
    root = settings.FUNKWHALE_URL
    if path.startswith("/") and root.endswith("/"):
        return root + path[1:]
    elif not path.startswith("/") and not root.endswith("/"):
        return root + "/" + path
    else:
        return root + path


def clean_wsgi_headers(raw_headers):
    """
    Convert WSGI headers from CONTENT_TYPE to Content-Type notation
    """
    cleaned = {}
    non_prefixed = ["content_type", "content_length"]
    for raw_header, value in raw_headers.items():
        h = raw_header.lower()
        if not h.startswith("http_") and h not in non_prefixed:
            continue

        words = h.replace("http_", "", 1).split("_")
        cleaned_header = "-".join([w.capitalize() for w in words])
        cleaned[cleaned_header] = value

    return cleaned


def slugify_username(username):
    """
    Given a username such as "hello M. world", returns a username
    suitable for federation purpose (hello_M_world).

    Preserves the original case.

    Code is borrowed from django's slugify function.
    """

    value = str(username)
    value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    value = re.sub(r"[^\w\s-]", "", value).strip()
    return re.sub(r"[-\s]+", "_", value)


def retrieve_ap_object(
    fid, actor, serializer_class=None, queryset=None, apply_instance_policies=True
):
    # we have a duplicate check here because it's less expensive to do those checks
    # twice than to trigger a HTTP request
    payload, updated = mrf.inbox.apply({"id": fid})
    if not payload:
        raise exceptions.BlockedActorOrDomain()
    if queryset:
        try:
            # queryset can also be a Model class
            existing = queryset.filter(fid=fid).first()
        except AttributeError:
            existing = queryset.objects.filter(fid=fid).first()
        if existing:
            return existing

    auth = (
        None if not actor else signing.get_auth(actor.private_key, actor.private_key_id)
    )
    response = session.get_session().get(
        fid,
        auth=auth,
        headers={
            "Accept": "application/activity+json",
            "Content-Type": "application/activity+json",
        },
    )
    response.raise_for_status()
    data = response.json()

    # we match against mrf here again, because new data may yield different
    # results
    data, updated = mrf.inbox.apply(data)
    if not data:
        raise exceptions.BlockedActorOrDomain()

    if not serializer_class:
        return data
    serializer = serializer_class(data=data, context={"fetch_actor": actor})
    serializer.is_valid(raise_exception=True)
    return serializer.save()


def get_domain_query_from_url(domain, url_field="fid"):
    """
    Given a domain name and a field, will return a Q() object
    to match objects that have this domain in the given field.
    """

    query = Q(**{"{}__startswith".format(url_field): "http://{}/".format(domain)})
    query = query | Q(
        **{"{}__startswith".format(url_field): "https://{}/".format(domain)}
    )
    return query


def local_qs(queryset, url_field="fid", include=True):
    query = get_domain_query_from_url(
        domain=settings.FEDERATION_HOSTNAME, url_field=url_field
    )
    if not include:
        query = ~query
    return queryset.filter(query)


def is_local(url):
    if not url:
        return True

    d = settings.FEDERATION_HOSTNAME
    return url.startswith("http://{}/".format(d)) or url.startswith(
        "https://{}/".format(d)
    )


def get_actor_data_from_username(username):

    parts = username.split("@")

    return {
        "username": parts[0],
        "domain": parts[1] if len(parts) > 1 else settings.FEDERATION_HOSTNAME,
    }


def get_actor_from_username_data_query(field, data):
    if not data:
        return Q(**{field: None})
    if field:
        return Q(
            **{
                "{}__preferred_username__iexact".format(field): data["username"],
                "{}__domain__name__iexact".format(field): data["domain"],
            }
        )
    else:
        return Q(
            **{
                "preferred_username__iexact": data["username"],
                "domain__name__iexact": data["domain"],
            }
        )

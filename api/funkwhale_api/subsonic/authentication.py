import binascii
import hashlib

from rest_framework import authentication, exceptions

from funkwhale_api.users.models import User

from funkwhale_api.plugins import authentication as plugin_authentication


def get_token(salt, password):
    to_hash = password + salt
    h = hashlib.md5()
    h.update(to_hash.encode("utf-8"))
    return h.hexdigest()


def authenticate(username, password):
    try:
        if password.startswith("enc:"):
            password = password.replace("enc:", "", 1)
            password = binascii.unhexlify(password).decode("utf-8")
        user = User.objects.select_related("actor").get(
            username__iexact=username, is_active=True, subsonic_api_token=password
        )
    except (User.DoesNotExist, binascii.Error):
        raise exceptions.AuthenticationFailed("Wrong username or password.")

    return (user, None)


def authenticate_salt(username, salt, token):
    try:
        user = User.objects.select_related("actor").get(
            username=username, is_active=True, subsonic_api_token__isnull=False
        )
    except User.DoesNotExist:
        raise exceptions.AuthenticationFailed("Wrong username or password.")
    expected = get_token(salt, user.subsonic_api_token)
    if expected != token:
        raise exceptions.AuthenticationFailed("Wrong username or password.")

    return (user, None)


class SubsonicAuthentication(
    plugin_authentication.AttachPluginsConfMixin, authentication.BaseAuthentication
):
    def authenticate(self, request):
        auth = self.perform_authentication(request)
        self.update_plugins_conf(request, auth)
        return auth

    def perform_authentication(self, request):
        data = request.GET or request.POST
        username = data.get("u")
        if not username:
            return None

        p = data.get("p")
        s = data.get("s")
        t = data.get("t")
        if not p and (not s or not t):
            raise exceptions.AuthenticationFailed("Missing credentials")

        if p:
            return authenticate(username, p)
        return authenticate_salt(username, s, t)

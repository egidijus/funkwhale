class Scope:
    def __init__(self, id, label="", children=None):
        self.id = id
        self.label = ""
        self.children = children or []

    def copy(self, prefix):
        return Scope("{}:{}".format(prefix, self.id))


BASE_SCOPES = [
    Scope(
        "profile", "Access profile data (email, username, avatar, subsonic password…)"
    ),
    Scope("libraries", "Access uploads, libraries, and audio metadata"),
    Scope("edits", "Browse and submit edits on audio metadata"),
    Scope("follows", "Access library follows"),
    Scope("favorites", "Access favorites"),
    Scope("filters", "Access content filters"),
    Scope("listenings", "Access listening history"),
    Scope("radios", "Access radios"),
    Scope("playlists", "Access playlists"),
    Scope("notifications", "Access personal notifications"),
    Scope("security", "Access security settings"),
    Scope("reports", "Access reports"),
    Scope("plugins", "Access plugins"),
    # Privileged scopes that require specific user permissions
    Scope("instance:settings", "Access instance settings"),
    Scope("instance:users", "Access local user accounts"),
    Scope("instance:invitations", "Access invitations"),
    Scope("instance:edits", "Access instance metadata edits"),
    Scope(
        "instance:libraries", "Access instance uploads, libraries and audio metadata"
    ),
    Scope("instance:accounts", "Access instance federated accounts"),
    Scope("instance:domains", "Access instance domains"),
    Scope("instance:policies", "Access instance moderation policies"),
    Scope("instance:reports", "Access instance moderation reports"),
    Scope("instance:requests", "Access instance moderation requests"),
    Scope("instance:notes", "Access instance moderation notes"),
]
SCOPES = [
    Scope("read", children=[s.copy("read") for s in BASE_SCOPES]),
    Scope("write", children=[s.copy("write") for s in BASE_SCOPES]),
]


def flatten(*scopes):
    for scope in scopes:
        yield scope
        yield from flatten(*scope.children)


SCOPES_BY_ID = {s.id: s for s in flatten(*SCOPES)}

FEDERATION_REQUEST_SCOPES = {"read:libraries"}
ANONYMOUS_SCOPES = {
    "read:libraries",
    "read:playlists",
    "read:listenings",
    "read:favorites",
    "read:radios",
    "read:edits",
}

COMMON_SCOPES = ANONYMOUS_SCOPES | {
    "read:profile",
    "write:profile",
    "write:libraries",
    "write:playlists",
    "read:follows",
    "write:follows",
    "write:favorites",
    "read:notifications",
    "write:notifications",
    "write:radios",
    "write:edits",
    "read:filters",
    "write:filters",
    "read:reports",
    "write:reports",
    "write:listenings",
}

LOGGED_IN_SCOPES = COMMON_SCOPES | {
    "read:security",
    "write:security",
    "read:plugins",
    "write:plugins",
}

# We don't allow admin access for oauth apps yet
OAUTH_APP_SCOPES = COMMON_SCOPES


def get_from_permissions(**permissions):
    from funkwhale_api.users import models

    final = LOGGED_IN_SCOPES
    for permission_name, value in permissions.items():
        if value is False:
            continue
        config = models.PERMISSIONS_CONFIGURATION[permission_name]
        final = final | config["scopes"]
    return final

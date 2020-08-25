"""
A plugin that enables scrobbling to ListenBrainz and Last.fm.

If you're scrobbling to last.fm, you will need to create an `API account <https://www.last.fm/api/account/create>`_
and add two variables two your .env file:

- ``FUNKWHALE_PLUGIN_SCROBBLER_LASTFM_API_KEY=apikey``
- ``FUNKWHALE_PLUGIN_SCROBBLER_LASTFM_API_SECRET=apisecret``

"""
from config import plugins

PLUGIN = plugins.get_plugin_config(
    name="scrobbler",
    label="Scrobbler",
    description="A plugin that enables scrobbling to ListenBrainz and Last.fm",
    version="0.1",
    user=True,
    conf=[
        {
            "name": "url",
            "type": "url",
            "allow_null": True,
            "allow_blank": True,
            "required": False,
            "label": "URL of the scrobbler service",
            "help": (
                "Suggested choices:\n\n"
                "- LastFM (default if left empty): http://post.audioscrobbler.com\n"
                "- ListenBrainz: http://proxy.listenbrainz.org/\n"
                "- Libre.fm: http://turtle.libre.fm/"
            ),
        },
        {"name": "username", "type": "text", "label": "Your scrobbler username"},
        {"name": "password", "type": "password", "label": "Your scrobbler password"},
    ],
    # settings=[
    #     {"name": "lastfm_api_key", "type": "text"},
    #     {"name": "lastfm_api_secret", "type": "text"},
    # ]
)

Importing music from the server
===============================

Funkwhale can import music files that are located on the server assuming
they readable by the Funkwhale application. Your music files should contain at
least an ``artist``, ``album`` and ``title`` tags, but we recommend you tag
it extensively using a proper tool, such as Beets or Musicbrainz Picard.

Funkwhale supports two different import modes:

- copy (the default): files are copied into Funkwhale's internal storage. This means importing a 1GB library will result in the same amount of space being used by Funkwhale.
- :ref:`in-place <in-place-import>` (when the ``--in-place`` is provided): files are referenced in Funkwhale's DB but not copied or touched in anyway. This is useful if you have a huge library, or one that is updated by an external tool such as Beets.

.. note::

    In Funkwhale 1.0, **the default behaviour will change to in-place import**

Regardless of the mode you're choosing, import works as described below, assuming your files are located in
``/srv/funkwhale/data/music``:

.. code-block:: bash

    export LIBRARY_ID="<your_libary_id>"
    python api/manage.py import_files $LIBRARY_ID "/srv/funkwhale/data/music/" --recursive --noinput

.. note::
    You'll have to create a library in the Web UI before to get your library ID. Simply visit
    https://yourdomain/content/libraries/ to create one.

    Library IDs are available in library urls or sharing link. In this example:
    https://funkwhale.instance/content/libraries/769a2ae3-eb3d-4aff-9f94-2c4d80d5c2d1,
    the library ID is 769a2bc3-eb1d-4aff-9f84-2c4d80d5c2d1

    You can use only the first characters of the ID when calling the command, like that:
    ``export LIBRARY_ID="769a2bc3"``

When you use docker, the ``/srv/funkwhale/data/music`` is mounted from the host
to the ``/music`` directory on the container:

.. code-block:: bash

    export LIBRARY_ID="<your_libary_id>"
    docker-compose run --rm api python manage.py import_files $LIBRARY_ID "/music/" --recursive --noinput

When you installed Funkwhale via ansible, you need to call a script instead of Python, and the folder path must be adapted accordingly:

.. code-block:: bash

    export LIBRARY_ID="<your_libary_id>"
    /srv/funkwhale/manage import_files $LIBRARY_ID "/srv/funkwhale/data/music/" --recursive --noinput


The import command supports several options, and you can check the help to
get details::

    docker-compose run --rm api python manage.py import_files --help

.. note::

    For the best results, we recommend tagging your music collection through
    `Picard <http://picard.musicbrainz.org/>`_ in order to have the best quality metadata.

.. note::

    This command is idempotent, meaning you can run it multiple times on the same
    files and already imported files will simply be skipped.

.. note::

    At the moment, only Flac, OGG/Vorbis and MP3 or AIFF files with ID3 tags are supported



.. _in-place-import:

In-place import
^^^^^^^^^^^^^^^

By default, the CLI-importer will copy imported files to Funkwhale's internal
storage. This means importing a 1GB library will result in the same amount
of space being used by Funkwhale.

While this behaviour has some benefits (easier backups and configuration),
it's not always the best choice, especially if you have a huge library
to import and don't want to double your disk usage.

The CLI importer supports an additional ``--in-place`` option that triggers the
following behaviour during import:

1. Imported files are not store in Funkwhale anymore
2. Instead, Funkwhale will store the file path and use it to serve the music

Because those files are not managed by Funkwhale, we offer additional
configuration options to ensure the webserver can serve them properly:

- :ref:`setting-MUSIC_DIRECTORY_PATH`
- :ref:`setting-MUSIC_DIRECTORY_SERVE_PATH`

We recommend you symlink all your music directories into ``/srv/funkwhale/data/music``
and run the `import_files` command from that directory. This will make it possible
to use multiple music directories, without any additional configuration
on the webserver side.

For instance, if you have a NFS share with your music mounted at ``/media/mynfsshare``,
you can create a symlink like this::

    ln -s /media/mynfsshare /srv/funkwhale/data/music/nfsshare

And import music from this share with this command::

    export LIBRARY_ID="<your_libary_id>"
    python api/manage.py import_files $LIBRARY_ID "/srv/funkwhale/data/music/nfsshare/" --recursive --noinput --in-place

On docker setups, it will require a bit more work, because while the ``/srv/funkwhale/data/music`` is mounted
in containers, symlinked directories are not.

To fix that, you can use bind mounts instead of symbolic links, as it replicates the source directory tree. With the previous NFS share, it would go this way::

    mount --bind /media/mynfsshare /srv/funkwhale/data/music/nfsshare

If you want to go with symlinks, ensure each symlinked directory is mounted as a volume as well in your ``docker-compose.yml`` file::

    celeryworker:
      volumes:
      - ./data/music:/music:ro
      - ./data/media:/app/funkwhale_api/media
      # add your symlinked dirs here
      - /media/nfsshare:/media/nfsshare:ro

    api:
      volumes:
      - ./data/music:/music:ro
      - ./data/media:/app/funkwhale_api/media
      # add your symlinked dirs here
      - /media/nfsshare:/media/nfsshare:ro

Metadata updates
^^^^^^^^^^^^^^^^

When doing an import with in ``in-place`` mode, the importer will also check and update existing entries
found in the database. For instance, if a file was imported, the ID3 Title tag was updated, and you rerun a scan,
Funkwhale will pick up the new title. The following fields can be updated this way:

- Track mbid
- Track title
- Track position and disc number
- Track license and copyright
- Track genre
- Album cover
- Album title
- Album mbid
- Album release date
- Artist name
- Artist mbid
- Album artist name
- Album artist mbid


React to filesystem events with ``--watch``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you have a really big library or one that is updated quite often, running the ``import_files`` command by hand
may not be practical. To help with this use case, the ``import_files`` command supports a ``--watch`` flag that will observes filesystem events
instead of performing a full import.

File creation, move, update and removal are handled when ``--watch`` is provided:

- Files created in the watched directory are imported immediatly
- If using ``in-place`` mode, files updates trigger a metadata update on the corresponding entries
- If using ``in-place`` mode, files that are moved and known by Funkwhale will see their path updated in Funkwhale's DB
- If using ``in-place`` mode, files that are removed and known by Funkwhale will be removed from Funkwhale's DB

Pruning dangling metadata with ``--prune``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Funkwhale is, by design, conservative with music metadata in its database. If you remove a file from Funkwhale's DB,
the corresponding artist, album and track object won't be deleted by default.

If you want to prune dangling metadata from the database once the ``import_files`` command is over, simply add the ``--prune`` flag.
This also works in with ``--watch``.

Album covers
^^^^^^^^^^^^

Whenever possible, Funkwhale will import album cover, with the following precedence:

1. It will use the cover embedded in the audio files themeselves, if any (Flac/MP3 only)
2. It will use a cover.jpg or a cover.png file from the imported track directory, if any
3. It will fetch cover art from musicbrainz, assuming the file is tagged correctly

Getting demo tracks
^^^^^^^^^^^^^^^^^^^

If you do not have any music on your server but still want to test the import
process, you can call the following methods do download a few albums licenced
under creative commons (courtesy of Jamendo):

.. parsed-literal::

    curl -L -o download-tracks.sh "https://dev.funkwhale.audio/funkwhale/funkwhale/raw/|version|/demo/download-tracks.sh"
    curl -L -o music.txt "https://dev.funkwhale.audio/funkwhale/funkwhale/raw/|version|/demo/music.txt"
    chmod +x download-tracks.sh
    ./download-tracks.sh music.txt

This will download a bunch of zip archives (one per album) under the ``data/music`` directory and unzip their content.

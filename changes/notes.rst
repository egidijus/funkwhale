Next release notes
==================

.. note::

    Those release notes refer to the current development branch and are reset
    after each release.


Dropped python 3.5 support [manual action required, non-docker only]
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

With Funkwhale 1.0, we're dropping support for Python 3.5. Before upgrading,
ensure ``python3 --version`` returns ``3.6`` or higher.

If it returns ``3.6`` or higher, you have nothing to do.

If it returns ``3.5``, you will need to upgrade your Python version/Host, then recreate your virtual environment::

    rm -rf /srv/funkwhale/virtualenv
    python3 -m venv /srv/funkwhale/virtualenv


Increased quality of JPEG thumbnails [manual action required]
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default quality for JPEG thumbnails was increased from 70 to 95, as 70 was producing visible artifacts in resized images.

Because of this change, existing thumbnails will not load, and you will need to:

1. delete the ``__sized__`` directory in your ``MEDIA_ROOT`` directory
2. run ``python manage.py fw media generate-thumbnails`` to regenerate thumbnails with the enhanced quality

If you don't want to regenerate thumbnails, you can keep the old ones by adding ``THUMBNAIL_JPEG_RESIZE_QUALITY=70`` to your .env file.

Small API breaking change in ``/api/v1/libraries``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To allow easier crawling of public libraries on a pod,we had to make a slight breaking change
to the behaviour of ``GET /api/v1/libraries``.

Before, it returned only libraries owned by the current user.

Now, it returns all the accessible libraries (including ones from other users and pods).

If you are consuming the API via a third-party client and need to retrieve your libraries,
use the ``scope`` parameter, like this: ``GET /api/v1/libraries?scope=me``

API breaking change in ``/api/v1/albums``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To increase performance, querying ``/api/v1/albums`` doesn't return album tracks anymore. This caused
some performance issues, especially as some albums and series have dozens or even hundreds of tracks.

If you want to retrieve tracks for an album, you can query ``/api/v1/tracks/?album=<albumid>``.
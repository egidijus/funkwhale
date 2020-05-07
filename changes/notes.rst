Next release notes
==================

.. note::

    Those release notes refer to the current development branch and are reset
    after each release.


Increased quality of JPEG thumbnails [manual action required]
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default quality for JPEG thumbnails was increased from 70 to 95, as 70 was producing visible artifacts in resized images.

Because of this change, existing thumbnails will not load, and you will need to:

1. delete the ``__sized__`` directory in your ``MEDIA_ROOT`` directory
2. run ``python manage.py fw media generate-thumbnails`` to regenerate thumbnails with the enhanced quality

If you don't want to regenerate thumbnails, you can keep the old ones by adding ``THUMBNAIL_JPEG_RESIZE_QUALITY=70`` to your .env file.

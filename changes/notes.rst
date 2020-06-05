Next release notes
==================

.. note::

    Those release notes refer to the current development branch and are reset
    after each release.

Small API breaking change in ``/api/v1/libraries``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To allow easier crawling of public libraries on a pod,we had to make a slight breaking change
to the behaviour of ``GET /api/v1/libraries``.

Before, it returned only libraries owned by the current user.

Now, it returns all the accessible libraries (including ones from other users and pods).

If you are consuming the API via a third-party client and need to retrieve your libraries,
use the ``scope`` parameter, like this: ``GET /api/v1/libraries?scope=me``

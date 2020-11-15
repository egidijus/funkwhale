Upgrading your Funkwhale instance to a newer version
====================================================

.. note::

    Before upgrading your instance, we strongly advise you to make at least a database backup. Ideally, you should make a full backup, including
    the database and the media files.

    We're commited to make upgrade as easy and straightforward as possible,
    however, Funkwhale is still in development and you'll be safer with a backup.


Reading the release notes
-------------------------

Please take a few minutes to read the :doc:`../changelog`: updates should work
similarly from version to version, but some of them may require additional steps.
Those steps would be described in the version release notes.


Insights about new versions
---------------------------

Some versions may be bigger than usual, and we'll try to detail the changes
when possible.

.. toctree::
   :maxdepth: 1

   0.17


Docker setup
------------

If you've followed the setup instructions in :doc:`../installation/docker`, upgrade path is
easy:

Mono-container installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Basically, you need to pull the new container image, stop and delete your existing container,
and relaunch a new one:

To upgrade your service, change the version number of the image in ``docker-compose.yml`` with the latest release (i.e. |version|).

Pull the new images:

.. code-block:: shell

    docker-compose pull

Restart the service:

.. code-block:: shell

    docker-compose up -d

Multi-container installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. parsed-literal::
    # this assumes you want to upgrade to version "|version|"
    export FUNKWHALE_VERSION="|version|"

.. code-block:: shell

    cd /srv/funkwhale
    # hardcode the targeted version your env file
    # (look for the FUNKWHALE_VERSION variable)
    nano .env
    # Load your environment variables
    source .env
    # Download newest nginx configuration file
    curl -L -o nginx/funkwhale.template "https://dev.funkwhale.audio/funkwhale/funkwhale/raw/$FUNKWHALE_VERSION/deploy/docker.nginx.template"
    curl -L -o nginx/funkwhale_proxy.conf "https://dev.funkwhale.audio/funkwhale/funkwhale/raw/$FUNKWHALE_VERSION/deploy/docker.funkwhale_proxy.conf"
    # Pull the new version containers
    docker-compose pull
    # Apply the database migrations
    docker-compose run --rm api python manage.py migrate
    # Relaunch the containers
    docker-compose up -d

.. warning::

    You may sometimes get the following warning while applying migrations::

        "Your models have changes that are not yet reflected in a migration, and so won't be applied."

    This is a warning, not an error, and it can be safely ignored.
    Never run the ``makemigrations`` command yourself.

Upgrading the Postgres container
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

With some Funkwhale releases, it is recommended to upgrade the version of the
Postgres database server container. For example, Funkwhale 0.17 recommended
Postgres 9.4, but Funkwhale 0.18 recommends Postgres 11. When upgrading
Postgres, it is not sufficient to change the container referenced in
``docker-compose.yml``. New major versions of Postgres cannot read the databases
created by older major versions. The data has to be exported from a running
instance of the old version and imported by the new version.

Thankfully, there is a Docker container available to automate this process. You
can use the following snippet to upgrade your database in ``./postgres``,
keeping a backup of the old version in ``./postgres-old``:

.. code-block:: shell

    # Replace "9.4" and "11" with the versions you are migrating between.
    export OLD_POSTGRES=9.4
    export NEW_POSTGRES=11
    docker-compose stop postgres
    docker run --rm \
      -v $(pwd)/data/postgres:/var/lib/postgresql/${OLD_POSTGRES}/data \
      -v $(pwd)/data/postgres-new:/var/lib/postgresql/${NEW_POSTGRES}/data \
      tianon/postgres-upgrade:${OLD_POSTGRES}-to-${NEW_POSTGRES}
    # Add back the access control rule that doesn't survive the upgrade
    echo "host all all all trust" | sudo tee -a ./data/postgres-new/pg_hba.conf
    # Swap over to the new database
    mv ./data/postgres ./data/postgres-old
    mv ./data/postgres-new ./data/postgres


Non-docker setup
----------------

If you installed Funkwhale using the install script, upgrading is done using ``sh -c "$(curl -sSL https://get.funkwhale.audio/upgrade.sh)"``. Make sure to run this command with root permissions.

If you manually installed Funkwhale, please use the following instructions.

Upgrade the static files
^^^^^^^^^^^^^^^^^^^^^^^^

On non-docker setups, the front-end app
is updated separately from the API. This is as simple as downloading
the zip with the static files and extracting it in the correct place.

The following example assume your setup match :ref:`frontend-setup`.

.. parsed-literal::

    # this assumes you want to upgrade to version "|version|"
    export FUNKWHALE_VERSION="|version|"
    cd /srv/funkwhale
    sudo -u funkwhale curl -L -o front.zip "https://dev.funkwhale.audio/funkwhale/funkwhale/builds/artifacts/$FUNKWHALE_VERSION/download?job=build_front"
    sudo -u funkwhale unzip -o front.zip
    sudo -u funkwhale rm front.zip

Upgrading the API
^^^^^^^^^^^^^^^^^

.. note::

    Starting with Funkwhale 0.20, it is recommended you run Funkwhale with Python 3.6 or greater. This means upgrading to
    Debian 10 if you're on Debian 9.

    If you still want to use Python 3.5, you can, but you'll need to run ``sudo -u funkwhale -H -E /srv/funkwhale/virtualenv/bin/pip install "uvicorn==0.8.6"`` before upgrading.

On non-docker, upgrade involves a few more commands. We assume your setup
match what is described in :doc:`/installation/debian`:

.. parsed-literal::

    # this assumes you want to upgrade to version "|version|"
    export FUNKWHALE_VERSION="|version|"
    cd /srv/funkwhale

    # download more recent API files
    sudo -u funkwhale curl -L -o "api-$FUNKWHALE_VERSION.zip" "https://dev.funkwhale.audio/funkwhale/funkwhale/-/jobs/artifacts/$FUNKWHALE_VERSION/download?job=build_api"
    sudo -u funkwhale unzip "api-$FUNKWHALE_VERSION.zip" -d extracted
    sudo -u funkwhale rm -rf api/ && sudo -u funkwhale mv extracted/api .
    sudo -u funkwhale rm -rf extracted
    sudo -u funkwhale rm api-$FUNKWHALE_VERSION.zip

    # update os dependencies
    sudo api/install_os_dependencies.sh install
    sudo -u funkwhale -H -E /srv/funkwhale/virtualenv/bin/pip install -r api/requirements.txt

    # collect static files
    sudo -u funkwhale -H -E /srv/funkwhale/virtualenv/bin/python api/manage.py collectstatic --no-input

    # stop the services
    sudo systemctl stop funkwhale.target

    # apply database migrations
    sudo -u funkwhale -H -E /srv/funkwhale/virtualenv/bin/python api/manage.py migrate

    # restart the services
    sudo systemctl start funkwhale.target

.. note::
    If you see a PermissionError when running the ``migrate`` command, try running the following commands by hand, and relaunch the migrations::

        sudo -u postgres psql funkwhale -c 'CREATE EXTENSION IF NOT EXISTS "citext";'
        sudo -u postgres psql funkwhale -c 'CREATE EXTENSION IF NOT EXISTS "unaccent";'

.. warning::

    You may sometimes get the following warning while applying migrations::

        "Your models have changes that are not yet reflected in a migration, and so won't be applied."

    This is a warning, not an error, and it can be safely ignored.
    Never run the ``makemigrations`` command yourself.

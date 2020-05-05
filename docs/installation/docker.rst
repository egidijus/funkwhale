Docker installation
===================

Docker is the easiest way to get a Funkwhale instance up and running.

We support two types of Docker deployments:

- :ref:`Mono-container <docker-mono-container>`: all processes live in the same container (database, nginx, redis, etc.). It's easier to deploy and to integrate with container management systems like Portainer. However, it's not possible to scale this type of deployment on multiple servers.
- :ref:`Multi-container <docker-multi-container>`: each process lives in a dedicated container. This setup is more involved but also more flexible and scalable.

.. note::

    We do not distribute Docker images for non-amd64 architectures yet. However, :doc:`you can easily build
    those images yourself following our instructions <non_amd64_architectures>`, and come back to this installation guide once
    the build is over.

.. _docker-mono-container:

Mono-container installation
---------------------------

.. note::

    This installation method was contributed by @thetarkus, at https://github.com/thetarkus/docker-funkwhale

These are the installation steps:

1. Install docker
2. Create ``funkwhale`` user
3. Create ``.env`` file
4. Create ``docker-compose.yml`` file
5. Start Funkwhale service

Install docker
~~~~~~~~~~~~~~

Ensure you have `Docker <https://docs.docker.com/engine/installation/>`_ and `docker-compose <https://docs.docker.com/compose/install/>`_ installed.

Create ``funkwhale`` user
~~~~~~~~~~~~~~~~~~~~~~~~~

Create the user and the directory:

.. code-block:: shell

    sudo useradd -r -s /usr/bin/nologin -m -d /srv/funkwhale -U -G docker funkwhale
    cd /srv/funkwhale

Log in as the newly created user from now on:

.. code-block:: shell

    sudo -u funkwhale -H bash

Create ``.env`` file
~~~~~~~~~~~~~~~~~~~~

Export the `version you want <https://hub.docker.com/r/funkwhale/all-in-one/tags>`_ to deploy (e.g., ``0.21``):

Create an env file to store a few important configuration options:

.. code-block:: shell

    touch .env
    chmod 600 .env  # reduce permissions on the .env file since it contains sensitive data
    cat > .env << EOF
    # Replace 'your.funkwhale.example' with your actual domain
    FUNKWHALE_HOSTNAME=your.funkwhale.example
    # Protocol may also be: http
    FUNKWHALE_PROTOCOL=https
    # This limits the upload size
    NGINX_MAX_BODY_SIZE=100M
    # Bind to localhost
    FUNKWHALE_API_IP=127.0.0.1
    # Container port you want to expose on the host
    FUNKWHALE_API_PORT=5000
    # Generate and store a secure secret key for your instance
    DJANGO_SECRET_KEY=$(openssl rand -hex 45)
    # Remove this if you expose the container directly on ports 80/443
    NESTED_PROXY=1
    EOF

Create ``docker-compose.yml`` file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    version: "3"
    services:
      funkwhale:
        container_name: funkwhale
        restart: unless-stopped
        # change version number here when you want to do an upgrade
        image: funkwhale/all-in-one:|version|
        env_file: .env
        environment:
          # adapt to the pid/gid that own /srv/funkwhale/data
          - PUID=1000
          - PGID=1000
        volumes:
          - /srv/funkwhale/data:/data
          - /path/to/your/music/dir:/music:ro
        ports:
          - "5000:80"

.. note::

    - ``PUID`` and ``PGID`` are optional but useful to prevent permission issues with docker volumes
    - ``/path/to/your/music/dir`` should point to a path on your host where music you would like to import is located. You can safely remove the volume if you don't want to import music that way.

Start Funkwhale service
~~~~~~~~~~~~~~~~~~~~~~~

Start the container:

.. code-block:: shell

    docker-compose up -d

Your container should start in the background, and your instance be available at ``yourip:5000`` shortly.

You will need an admin account to login and manage your account, create one using the following command: ``docker exec -it funkwhale manage createsuperuser``

Useful commands:

- You can start and stop your instance using ``docker-compose start`` and ``docker-compose stop``, respectively
- You can examine the logs by running ``docker logs -f --tail=50 funkwhale``
- To have a better idea of the resource usage of your instance (CPU, memory), run ``docker stats funkwhale``

Now, you just need to configure your :ref:`reverse-proxy <reverse-proxy-setup>`. Don't worry, it's quite easy.

.. note::

    To upgrade your service, change the version number in ``docker-compose.yml`` and re-run ``docker-compose up -d``.

    Don't forget you might have manual changes to do when upgrading to a newer version.

.. _docker-multi-container:

Multi-container installation
----------------------------

First, ensure you have `Docker <https://docs.docker.com/engine/installation/>`_ and `docker-compose <https://docs.docker.com/compose/install/>`_ installed.

Export the `version you want <https://hub.docker.com/r/funkwhale/all-in-one/tags>`_ to deploy (e.g., ``0.21``):

.. parsed-literal::

    export FUNKWHALE_VERSION="|version|"

Download the sample docker-compose file:

.. parsed-literal::

    mkdir /srv/funkwhale
    cd /srv/funkwhale
    mkdir nginx
    curl -L -o nginx/funkwhale.template "https://dev.funkwhale.audio/funkwhale/funkwhale/raw/${FUNKWHALE_VERSION}/deploy/docker.nginx.template"
    curl -L -o nginx/funkwhale_proxy.conf "https://dev.funkwhale.audio/funkwhale/funkwhale/raw/${FUNKWHALE_VERSION}/deploy/docker.funkwhale_proxy.conf"
    curl -L -o docker-compose.yml "https://dev.funkwhale.audio/funkwhale/funkwhale/raw/${FUNKWHALE_VERSION}/deploy/docker-compose.yml"

At this point, the architecture of ``/srv/funkwhale``  should look like that:

::

    .
    ├── docker-compose.yml
    └── nginx
        ├── funkwhale_proxy.conf
        └── funkwhale.template

Create your env file:

.. parsed-literal::

    curl -L -o .env "https://dev.funkwhale.audio/funkwhale/funkwhale/raw/${FUNKWHALE_VERSION}/deploy/env.prod.sample"
    sed -i "s/FUNKWHALE_VERSION=latest/FUNKWHALE_VERSION=$FUNKWHALE_VERSION/" .env
    chmod 600 .env  # reduce permissions on the .env file since it contains sensitive data
    sudo nano .env


Ensure to edit it to match your needs (this file is heavily commented), in particular ``DJANGO_SECRET_KEY`` and ``FUNKWHALE_HOSTNAME``.
You should take a look at the `configuration reference <https://docs.funkwhale.audio/configuration.html#configuration-reference>`_ for more detailed information regarding each setting.

Then, you should be able to pull the required images:

.. code-block:: bash

    docker-compose pull

Run the database container and the initial migrations:

.. code-block:: bash

    docker-compose up -d postgres
    docker-compose run --rm api python manage.py migrate

.. warning::

    You may sometimes get the following warning while applying migrations::

        "Your models have changes that are not yet reflected in a migration, and so won't be applied."

    This is a warning, not an error, and it can be safely ignored.
    Never run the ``makemigrations`` command yourself.

Create your admin user:

.. code-block:: bash

    docker-compose run --rm api python manage.py createsuperuser

Then launch the whole thing:

.. code-block:: bash

    docker-compose up -d

Now, you just need to configure your :ref:`reverse-proxy <reverse-proxy-setup>`. Don't worry, it's quite easy.

About music acquisition
-----------------------

If you want to :doc:`import music located on the server <../admin/importing-music>`, you can put it in the ``data/music`` directory and it will become readable by the importer.

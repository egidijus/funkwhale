Changing Your Instance URL
==========================

At some point, you may wish to change your instance URL. In order to
do this, you will need to change the following:

- The instance URL in your .env file
- The instance URL in your ``/etc/nginx/sites-enabled/funkwhale.conf`` or ``/etc/apache2/sites-enabled/funkwhale.conf`` depending on your web server setup
- Any references to the old URL in your database

The changes to the database can be achieved with the ``fix_federation_ids`` script in the ``manage.py``
file. 

Example output:

.. code-block:: shell

   # For Docker setups
   docker-compose run --rm api python manage.py fix_federation_ids https://old-url https://new-url --no-dry-run --no-input

   # For non-Docker setups
   python manage.py fix_federation_ids https://old-url https://new-url --no-dry-run --no-input

   # Output
   Will replace 108 found occurrences of 'https://old-url' by 'https://new-url':

   - 20 music.Artist
   - 13 music.Album
   - 39 music.Track
   - 31 music.Upload
   - 1 music.Library
   - 4 federation.Actor
   - 0 federation.Activity
   - 0 federation.Follow
   - 0 federation.LibraryFollow

   Replacing on 20 music.Artist…
   Replacing on 13 music.Album…
   Replacing on 39 music.Track…
   Replacing on 31 music.Upload…
   Replacing on 1 music.Library…
   Replacing on 4 federation.Actor…
   Replacing on 0 federation.Activity…
   Replacing on 0 federation.Follow…
   Replacing on 0 federation.LibraryFollow…

On Docker Installations
-----------------------

If you have followed the :doc:`Docker installation instructions <../installation/docker>`, you
will need to do the following:

- Edit your .env file to change the ``FUNKWHALE_HOSTNAME``  and ``DJANGO_ALLOWED_HOSTS`` value to your new URL
- Edit your ``/etc/nginx/sites-enabled/funkwhale.conf`` file to change the ``server_name`` values to your new URL
- Run the following command to change all mentions of your old instance URL in the database:

.. code-block:: shell

   docker-compose run --rm api python manage.py fix_federation_ids https://old-url https://new-url --no-dry-run --no-input

- Restart Nginx or Apache to pick up the new changes

.. code-block:: shell

   # For Nginx
   sudo systemctl restart nginx

   # For Apache
   sudo systemctl restart apache2

On Non-Docker Installations
---------------------------

If you have followed the :doc:`non-docker setup <../installation/debian>`, you will need to do the following:

- Edit your .env file to change the ``FUNKWHALE_HOSTNAME``  and ``DJANGO_ALLOWED_HOSTS`` value to your new URL
- Edit your ``/etc/nginx/sites-enabled/funkwhale.conf`` file to change the ``server_name`` values to your new URL
- Run the following command to change all mentions of your old instance URL in the database:

.. code-block:: shell

   python manage.py fix_federation_ids https://old-url https://new-url --no-dry-run --no-input

- Restart Nginx or Apache to pick up the new changes

.. code-block:: shell

   # For Nginx
   sudo systemctl restart nginx

   # For Apache
   sudo systemctl restart apache2
   
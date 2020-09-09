Contribute to Funkwhale development
===================================

First of all, thank you for your interest in the project! We really
appreciate the fact that you're about to take some time to read this
and hack on the project.

This document will guide you through common operations such as:

- Setup your development environment
- Working on your first issue
- Writing unit tests to validate your work
- Submit your work

A quick path to contribute on the front-end
-------------------------------------------

The next sections of this document include a full installation guide to help
you setup a local, development version of Funkwhale. If you only want to fix small things
on the front-end, and don't want to manage a full development environment, there is another way.

As the front-end can work with any Funkwhale server, you can work with the front-end only,
and make it talk with an existing instance (like the demo one, or you own instance, if you have one).

If even that is too much for you, you can also make your changes without any development environment,
and open a merge request. We will be able to review your work easily by spawning automatically a
live version of your changes, thanks to Gitlab Review apps.

Setup front-end only development environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Clone the repository::

    git clone ssh://git@dev.funkwhale.audio/funkwhale/funkwhale.git
    cd funkwhale
    cd front

2. Install `nodejs <https://nodejs.org/en/download/package-manager/>`_ and `yarn <https://yarnpkg.com/lang/en/docs/install/#debian-stable>`_

3. Install the dependencies::

    yarn install

4. Compile the translations::

    yarn i18n-compile

5. Launch the development server::

    # this will serve the front-end on http://localhost:8000/front/
    VUE_PORT=8000 yarn serve

6. Make the front-end talk with an existing server (like https://demo.funkwhale.audio or https://open.audio),
   by clicking on the corresponding link in the footer

7. Start hacking!

Setup your development environment
----------------------------------

If you want to fix a bug or implement a feature, you'll need
to run a local, development copy of funkwhale.

We provide a docker based development environment, which should
be both easy to setup and work similarly regardless of your
development machine setup.

Instructions for bare-metal setup will come in the future (Merge requests
are welcome).

Installing docker and docker-compose
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is already cover in the relevant documentations:

- https://docs.docker.com/install/
- https://docs.docker.com/compose/install/

Cloning the project
^^^^^^^^^^^^^^^^^^^

Visit https://dev.funkwhale.audio/funkwhale/funkwhale and clone the repository using SSH or HTTPS. Example using SSH::

    git clone ssh://git@dev.funkwhale.audio/funkwhale/funkwhale.git
    cd funkwhale

.. note::

    As of January 2020, the SSH fingerprints of our Gitlab server are the following::

        $ ssh-keyscan dev.funkwhale.audio | ssh-keygen -lf -
        # dev.funkwhale.audio:22 SSH-2.0-OpenSSH_7.4p1 Debian-10+deb9u6
        # dev.funkwhale.audio:22 SSH-2.0-OpenSSH_7.4p1 Debian-10+deb9u6
        # dev.funkwhale.audio:22 SSH-2.0-OpenSSH_7.4p1 Debian-10+deb9u6
        2048 SHA256:WEZ546nkMhB9yV9lyDZZcEeN/IfriyhU8+mj7Cz/+sU dev.funkwhale.audio (RSA)
        256 SHA256:dEhAo+1ImjC98hSqVdnkwVleheCulV8xIsV1eKUcig0 dev.funkwhale.audio (ECDSA)
        256 SHA256:/AxZwOSP74hlNKCHzmu9Trlp9zVGTrsJOV+zet1hYyQ dev.funkwhale.audio (ED25519)


A note about branches
^^^^^^^^^^^^^^^^^^^^^

Next release development occurs on the "develop" branch, and releases are made on the "master" branch. Therefore, when submitting Merge Requests, ensure you are merging on the develop branch.


Working with docker
^^^^^^^^^^^^^^^^^^^

In development, we use the docker-compose file named ``dev.yml``, and this is why all our docker-compose commands will look like this::

    docker-compose -f dev.yml logs

If you do not want to add the ``-f dev.yml`` snippet every time, you can run this command before starting your work::

    export COMPOSE_FILE=dev.yml


Creating your env file
^^^^^^^^^^^^^^^^^^^^^^

We provide a working .env.dev configuration file that is suitable for
development. However, to enable customization on your machine, you should
also create a .env file that will hold your personal environment
variables (those will not be commited to the project).

Create it like this::

    touch .env


Create docker network
^^^^^^^^^^^^^^^^^^^^^

Create the federation network::

    docker network create federation


Building the containers
^^^^^^^^^^^^^^^^^^^^^^^

On your initial clone, or if there have been some changes in the
app dependencies, you will have to rebuild your containers. This is done
via the following command::

    docker-compose -f dev.yml build


Database management
^^^^^^^^^^^^^^^^^^^

To setup funkwhale's database schema, run this::

    docker-compose -f dev.yml run --rm api python manage.py migrate

This will create all the tables needed for the API to run properly.
You will also need to run this whenever changes are made on the database
schema.

It is safe to run this command multiple times, so you can run it whenever
you fetch develop.


Development data
^^^^^^^^^^^^^^^^

You'll need at least an admin user and some artists/tracks/albums to work
locally.

Create an admin user with the following command::

    docker-compose -f dev.yml run --rm api python manage.py createsuperuser

Injecting fake data is done by running the following script::

    artists=25
    command="from funkwhale_api.music import fake_data; fake_data.create_data($artists)"
    echo $command | docker-compose -f dev.yml run --rm api python manage.py shell -i python

The previous command will create 25 artists with random albums, tracks
and metadata.


Launch all services
^^^^^^^^^^^^^^^^^^^

Before the first Funkwhale launch, it is required to run this::

    docker-compose -f dev.yml run --rm front yarn run i18n-compile

Then you can run everything with::

    docker-compose -f dev.yml up front api nginx celeryworker

This will launch all services, and output the logs in your current terminal window.
If you prefer to launch them in the background instead, use the ``-d`` flag, and access the logs when you need it via ``docker-compose -f dev.yml logs --tail=50 --follow``.

Once everything is up, you can access the various funkwhale's components:

- The Vue webapp, on http://localhost:8000
- The API, on http://localhost:8000/api/v1/
- The django admin, on http://localhost:800/api/admin/

Stopping everything
^^^^^^^^^^^^^^^^^^^

Once you're down with your work, you can stop running containers, if any, with::

    docker-compose -f dev.yml stop


Removing everything
^^^^^^^^^^^^^^^^^^^

If you want to wipe your development environment completely (e.g. if you want to start over from scratch), just run::

    docker-compose -f dev.yml down -v

This will wipe your containers and data, so please be careful before running it.

You can keep your data by removing the ``-v`` flag.


Working with federation locally
-------------------------------

This is not needed unless you need to work on federation-related features.

To achieve that, you'll need:

1. to update your dns resolver to resolve all your .dev hostnames locally
2. a reverse proxy (such as traefik) to catch those .dev requests and
   and with https certificate
3. two instances (or more) running locally, following the regular dev setup

Resolve .dev names locally
^^^^^^^^^^^^^^^^^^^^^^^^^^

If you use dnsmasq, this is as simple as doing::

    echo "address=/test/172.17.0.1" | sudo tee /etc/dnsmasq.d/test.conf
    sudo systemctl restart dnsmasq

If you use NetworkManager with dnsmasq integration, use this instead::

    echo "address=/test/172.17.0.1" | sudo tee /etc/NetworkManager/dnsmasq.d/test.conf
    sudo systemctl restart NetworkManager

Add wildcard certificate to the trusted certificates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Simply copy bundled certificates::

    sudo cp docker/ssl/test.crt /usr/local/share/ca-certificates/
    sudo update-ca-certificates

This certificate is a wildcard for ``*.funkwhale.test``

Run a reverse proxy for your instances
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Launch everything
^^^^^^^^^^^^^^^^^

Launch the traefik proxy::

    docker-compose -f docker/traefik.yml up -d

Then, in separate terminals, you can setup as many different instances as you
need::

    export COMPOSE_PROJECT_NAME=node2
    export VUE_PORT=1234  # this has to be unique for each instance
    docker-compose -f dev.yml run --rm api python manage.py migrate
    docker-compose -f dev.yml run --rm api python manage.py createsuperuser
    docker-compose -f dev.yml up nginx api front nginx api celeryworker

Note that by default, if you don't export the COMPOSE_PROJECT_NAME,
we will default to node1 as the name of your instance.

Assuming your project name is ``node1``, your server will be reachable
at ``https://node1.funkwhale.test/``. Not that you'll have to trust
the SSL Certificate as it's self signed.

When working on federation with traefik, ensure you have this in your ``env``::

    # This will ensure we don't bind any port on the host, and thus enable
    # multiple instances of funkwhale to be spawned concurrently.
    VUE_PORT_BINDING=
    # This disable certificate verification
    EXTERNAL_REQUESTS_VERIFY_SSL=false
    # this ensure you don't have incorrect urls pointing to http resources
    FUNKWHALE_PROTOCOL=https
    # Disable host ports binding for the nginx container, as traefik is serving everything
    NGINX_PORTS_MAPPING=80

Typical workflow for a contribution
-----------------------------------

0. Fork the project if you did not already or if you do not have access to the main repository
1. Checkout the development branch and pull most recent changes: ``git checkout develop && git pull``
2. If working on an issue, assign yourself to the issue. Otherwise, consider open an issue before starting to work on something, especially for new features.
3. Create a dedicated branch for your work ``42-awesome-fix``. It is good practice to prefix your branch name with the ID of the issue you are solving.
4. Work on your stuff
5. Commit small, atomic changes to make it easier to review your contribution
6. Add a changelog fragment to summarize your changes: ``echo "Implemented awesome stuff (#42)" > changes/changelog.d/42.feature``
7. Push your branch
8. Create your merge request
9. Take a step back and enjoy, we're really grateful you did all of this and took the time to contribute!

Changelog management
--------------------

To ensure we have extensive and well-structured changelog, any significant
work such as closing an issue must include a changelog fragment. Small changes
may include a changelog fragment as well but this is not mandatory. If you're not
sure about what to do, do not panic, open your merge request normally and we'll
figure everything during the review ;)

Changelog fragments are text files that can contain one or multiple lines
that describe the changes occurring in a bunch of commits. Those files reside
in ``changes/changelog.d``.

Content
^^^^^^^

A typical fragment looks like that:

    Fixed broken audio player on Chrome 42 for ogg files (#567)

If the work fixes one or more issues, the issue number should be included at the
end of the fragment (``(#567)`` is the issue number in the previous example).

If your work is not related to a specific issue, use the merge request
identifier instead, like this:

    Fixed a typo in landing page copy (!342)

Naming
^^^^^^

Fragment files should respect the following naming pattern: ``changes/changelog.d/<name>.<category>``.
Name can be anything describing your work, or simply the identifier of the issue number you are fixing.
Category can be one of:

- ``feature``: for new features
- ``enhancement``: for enhancements on existing features
- ``bugfix``: for bugfixes
- ``doc``: for documentation
- ``i18n``: for internationalization-related work
- ``misc``: for anything else

Shortcuts
^^^^^^^^^

Here is a shortcut you can use/adapt to easily create new fragments from command-line:

.. code-block:: bash

    issue="42"
    content="Fixed an overflowing issue on small resolutions (#$issue)"
    category="bugfix"
    echo $content > changes/changelog.d/$issue.$category

You can of course create fragments by hand in your text editor, or from Gitlab's
interface as well.

Internationalization
--------------------

We're using https://github.com/Polyconseil/vue-gettext to manage i18n in the project.

When working on the front-end, any end-user string should be marked as a translatable string,
with the proper context, as described below.

Translations in HTML
^^^^^^^^^^^^^^^^^^^^

Translations in HTML use the ``<translate>`` tag::

    <template>
      <div>
        <h1><translate translate-context="Content/Profile/Header">User profile</translate></h1>
        <p>
          <translate
            translate-context="Content/Profile/Paragraph"
            :translate-params="{username: 'alice'}">
            You are logged in as %{ username }
          </translate>
        </p>
         <p>
          <translate
            translate-context="Content/Profile/Paragraph"
            translate-plural="You have %{ count } new messages, that's a lot!"
            :translate-n="unreadMessagesCount"
            :translate-params="{count: unreadMessagesCount}">
            You have 1 new message
          </translate>
        </p>
      </div>
    </template>

Anything between the `<translate>` and `</translate>` delimiters will be considered as a translatable string.
You can use variables in the translated string via the ``:translate-params="{var: 'value'}"`` directive, and reference them like this:
``val value is %{ value }``.

For pluralization, you need to use ``translate-params`` in conjunction with ``translate-plural`` and ``translate-n``:

- ``translate-params`` should contain the variable you're using for pluralization (which is usually shown to the user)
- ``translate-n`` should match the same variable
- The ``<translate>`` delimiters contain the non-pluralized version of your string
- The ``translate-plural`` directive contains the pluralized version of your string


Translations in javascript
^^^^^^^^^^^^^^^^^^^^^^^^^^

Translations in javascript work by calling the ``this.$*gettext`` functions::

    export default {
      computed: {
        strings () {
          let tracksCount = 42
          let playButton = this.$pgettext('Sidebar/Player/Button/Verb, Short', 'Play')
          let loginMessage = this.$pgettext('*/Login/Message', 'Welcome back %{ username }')
          let addedMessage = this.$npgettext('*/Player/Message', 'One track was queued', '%{ count } tracks were queued', tracksCount)
          console.log(this.$gettextInterpolate(addedMessage, {count: tracksCount}))
          console.log(this.$gettextInterpolate(loginMessage, {username: 'alice'}))
        }
      }
    }

The first argument of the ``$pgettext`` and ``$npgettext`` functions is the string context.

Contextualization
^^^^^^^^^^^^^^^^^

Translation contexts provided via the ``translate-context`` directive and the ``$pgettext`` and ``$npgettext`` are never shown to end users
but visible by Funkwhale translators. They help translators where and how the strings are used,
especially with short or ambiguous strings, like ``May``, which can refer a month or a verb.

While we could in theory use free form context, like ``This string is inside a button, in the main page, and is a call to action``,
Funkwhale use a hierarchical structure to write contexts and keep them short and consistents accross the app. The previous context,
rewritten correctly would be: ``Content/Home/Button/Call to action``.

This hierarchical structure is made of several parts:

- The location part, which is required and refers to the big blocks found in Funkwhale UI where the translated string is displayed:
    - ``Content``
    - ``Footer``
    - ``Head``
    - ``Menu``
    - ``Popup``
    - ``Sidebar``
    - ``*`` for strings that are not tied to a specific location

- The feature part, which is required, and refers to the feature associated with the translated string:
    - ``About``
    - ``Admin``
    - ``Album``
    - ``Artist``
    - ``Embed``
    - ``Home``
    - ``Login``
    - ``Library``
    - ``Moderation``
    - ``Player``
    - ``Playlist``
    - ``Profile``
    - ``Favorites``
    - ``Notifications``
    - ``Radio``
    - ``Search``
    - ``Settings``
    - ``Signup``
    - ``Track``
    - ``Queue``
    - ``*`` for strings that are not tied to a specific feature

- The component part, which is required and refers to the type of element that contain the string:
    - ``Button``
    - ``Card``
    - ``Checkbox``
    - ``Dropdown``
    - ``Error message``
    - ``Form``
    - ``Header``
    - ``Help text``
    - ``Hidden text``
    - ``Icon``
    - ``Input``
    - ``Image``
    - ``Label``
    - ``Link``
    - ``List item``
    - ``Menu``
    - ``Message``
    - ``Paragraph``
    - ``Placeholder``
    - ``Tab``
    - ``Table``
    - ``Title``
    - ``Tooltip``
    - ``*`` for strings that are not tied to a specific component

The detail part, which is optional and refers to the contents of the string itself, such as:
    - ``Adjective``
    - ``Call to action``
    - ``Noun``
    - ``Short``
    - ``Unit``
    - ``Verb``

Here are a few examples of valid context hierarchies:

- ``Sidebar/Player/Button``
- ``Content/Home/Button/Call to action``
- ``Footer/*/Help text``
- ``*/*/*/Verb, Short``
- ``Popup/Playlist/Button``
- ``Content/Admin/Table.Label/Short, Noun (Value is a date)``

It's possible to nest multiple component parts to reach a higher level of detail. The component parts are then separated by a dot:

- ``Sidebar/Queue/Tab.Title``
- ``Content/*/Button.Title``
- ``Content/*/Table.Header``
- ``Footer/*/List item.Link``
- ``Content/*/Form.Help text``

Collecting translatable strings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want to ensure your translatable strings are correctly marked for translation,
you can try to extract them.

Extraction is done by calling ``yarn run i18n-extract``, which
will pull all the strings from source files and put them in a PO files.

You can then inspect the PO files to ensure everything is fine (but don't commit them, it's not needed).

Contributing to the API
-----------------------

Project structure
^^^^^^^^^^^^^^^^^

.. code-block:: shell

    tree api -L 2 -d
    api
    ├── config          # configuration directory (settings, urls, wsgi server)
    │   └── settings    # Django settings files
    ├── funkwhale_api   # project directory, all funkwhale logic is here
    ├── requirements    # python requirements files
    └── tests           # test files, matches the structure of the funkwhale_api directory

.. note::

    Unless trivial, API contributions must include unittests to ensure
    your fix or feature is working as expected and won't break in the future

Running tests
^^^^^^^^^^^^^

To run the pytest test suite, use the following command::

    docker-compose -f dev.yml run --rm api pytest

This is regular pytest, so you can use any arguments/options that pytest usually accept::

    # get some help
    docker-compose -f dev.yml run --rm api pytest -h
    # Stop on first failure
    docker-compose -f dev.yml run --rm api pytest -x
    # Run a specific test file
    docker-compose -f dev.yml run --rm api pytest tests/music/test_models.py

Writing tests
^^^^^^^^^^^^^

Although teaching you how to write unit tests is outside of the scope of this
document, you'll find below a collection of tips, snippets and resources
you can use if you want to learn on that subject.

Useful links:

- `A quick introduction to unit test writing with pytest <https://semaphoreci.com/community/tutorials/testing-python-applications-with-pytest>`_
- `A complete guide to Test-Driven Development (although not using Pytest) <https://www.obeythetestinggoat.com/>`_
- `pytest <https://docs.pytest.org/en/latest/>`_: documentation of our testing engine and runner
- `pytest-mock <https://pypi.org/project/pytest-mock/>`_: project page of our mocking engine
- `factory-boy <http://factoryboy.readthedocs.io/>`_: documentation of factory-boy, which we use to easily generate fake objects and data

Recommendations:

- Test files must target a module and mimic ``funkwhale_api`` directory structure: if you're writing tests for ``funkwhale_api/myapp/views.py``, you should put thoses tests in ``tests/myapp/test_views.py``
- Tests should be small and test one thing. If you need to test multiple things, write multiple tests.

We provide a lot of utils and fixtures to make the process of writing tests as
painless as possible. You'll find some usage examples below.

Use factories to create arbitrary objects:

.. code-block:: python

    # funkwhale_api/myapp/users.py

    def downgrade_user(user):
        """
        A simple function that remove superuser status from users
        and return True if user was actually downgraded
        """
        downgraded = user.is_superuser
        user.is_superuser = False
        user.save()
        return downgraded

    # tests/myapp/test_users.py
    from funkwhale_api.myapp import users

    def test_downgrade_superuser(factories):
        user = factories['users.User'](is_superuser=True)
        downgraded = users.downgrade_user(user)

        assert downgraded is True
        assert user.is_superuser is False

    def test_downgrade_normal_user_does_nothing(factories):
        user = factories['users.User'](is_superuser=False)
        downgraded = something.downgrade_user(user)

        assert downgraded is False
        assert user.is_superuser is False

.. note::

    We offer factories for almost if not all models. Factories are located
    in a ``factories.py`` file inside each app.

Mocking: mocking is the process of faking some logic in our code. This is
useful when testing components that depend on each other:

.. code-block:: python

    # funkwhale_api/myapp/notifications.py

    def notify(email, message):
        """
        A function that sends an email to the given recipient
        with the given message
        """

        # our email sending logic here
        # ...

    # funkwhale_api/myapp/users.py
    from . import notifications

    def downgrade_user(user):
        """
        A simple function that remove superuser status from users
        and return True if user was actually downgraded
        """
        downgraded = user.is_superuser
        user.is_superuser = False
        user.save()
        if downgraded:
            notifications.notify(user.email, 'You have been downgraded!')
        return downgraded

    # tests/myapp/test_users.py
    def test_downgrade_superuser_sends_email(factories, mocker):
        """
        Your downgrade logic is already tested, however, we want to ensure
        an email is sent when user is downgraded, but we don't have any email
        server available in our testing environment. Thus, we need to mock
        the email sending process.
        """
        mocked_notify = mocker.patch('funkwhale_api.myapp.notifications.notify')
        user = factories['users.User'](is_superuser=True)
        users.downgrade_user(user)

        # here, we ensure our notify function was called with proper arguments
        mocked_notify.assert_called_once_with(user.email, 'You have been downgraded')


    def test_downgrade_not_superuser_skips_email(factories, mocker):
        mocked_notify = mocker.patch('funkwhale_api.myapp.notifications.notify')
        user = factories['users.User'](is_superuser=True)
        users.downgrade_user(user)

        # here, we ensure no email was sent
        mocked_notify.assert_not_called()

Views: you can find some readable views tests in file: ``api/tests/users/test_views.py``

.. note::

    A complete list of available-fixtures is available by running
    ``docker-compose -f dev.yml run --rm api pytest --fixtures``


Contributing to the front-end
-----------------------------

Styles and themes
^^^^^^^^^^^^^^^^^

Our UI framework is Fomantic UI (https://fomantic-ui.com/), and Funkwhale's custom styles are written in SCSS. All the styles are configured in ``front/src/styles/_main.scss``,
including imporing of Fomantic UI styles and components.

We're applying several changes on top of the Fomantic CSS files, before they are imported:

1. Many hardcoded color values are replaced by CSS vars: e.g ``color: orange`` is replaced by ``color: var(--vibrant-color)``. This makes theming way easier.
2. Unused components variations and icons are stripped from the source files, in order to reduce the final size of our CSS files

This changes are applied automatically when running ``yarn install``, through a ``postinstall`` hook. Internally, ``front/scripts/fix-fomantic-css.py`` is called
and handle both kind of modifications. Please refer to this script if you need to use new icons to the project, or restore some components variations that
were stripped in order to use them.

Running tests
^^^^^^^^^^^^^

To run the front-end test suite, use the following command::

    docker-compose -f dev.yml run --rm front yarn test:unit

We also support a "watch and test" mode were we continually relaunch
tests when changes are recorded on the file system::

    docker-compose -f dev.yml run --rm front yarn test:unit -w

The latter is especially useful when you are debugging failing tests.

.. note::

    The front-end test suite coverage is still pretty low


Making a release
----------------

To make a new 3.4 release::

    # setup
    export NEXT_RELEASE=3.4  # replace with the next release number
    export PREVIOUS_RELEASE=3.3  # replace with the previous release number

    # ensure you have an up-to-date repo
    git checkout develop  # use master if you're doing a hotfix release
    git pull

    # compile changelog
    towncrier --version $NEXT_RELEASE --yes

    # polish changelog
    # - update the date
    # - look for typos
    # - add list of contributors via `python3 scripts/get-contributions-stats.py develop $PREVIOUS_RELEASE`
    nano CHANGELOG

    # Set the `__version__` variable to $NEXT_RELEASE
    nano api/funkwhale_api/__init__.py

    # commit
    git add .
    git commit -m "Version bump and changelog for $NEXT_RELEASE"

    # tag
    git tag $NEXT_RELEASE

    # publish
    git push --tags && git push

    # if you're doing a hotfix release from master
    git checkout develop && git merge master && git push

    # if you're doing a non-hotfix release, and a real release (not a real release) from develop
    git checkout master && git merge develop && git push

Then, visit https://dev.funkwhale.audio/funkwhale/funkwhale/-/tags, copy-paste the changelog on the corresponding
tag, and announce the good news ;)

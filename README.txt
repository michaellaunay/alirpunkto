alirpunkto
==========

AlirPunkto is a Python/Pyramid web application for cooperative membership and
account management, backed by LDAP, ZODB, Postfix and Apache.

The maintained documentation is now README.md. This legacy README.txt is kept as
a short entry point for tools or packaging workflows that still display it.

Quick start
-----------

    git clone git@github.com:michaellaunay/alirpunkto.git
    cd alirpunkto
    python3 -m venv .
    source bin/activate
    bin/pip install --upgrade pip setuptools wheel
    bin/pip install -e ".[testing]"
    mkdir -p var/log var/datas var/filestorage var/sessions
    cp .env.example .env
    python3 alirpunkto/generate_secret.py

Copy the generated SECRET_KEY into .env, then review LDAP, mail, site and SSO
settings.

Run tests
---------

    bin/pytest

Run the development server
--------------------------

    bin/pserve development.ini

Docker
------

Production stack:

    ./docker/init.sh
    docker compose --env-file docker/.env -f docker/docker-compose.yaml up -d

Local/offline test stack:

    ./docker/init_test.sh
    docker compose --env-file docker/.env.test -f docker/test-docker-compose.yaml up -d --build

More information
----------------

See README.md, docker/README.md and docker/README_TEST_LOCAL.md.

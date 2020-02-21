import os

from django import setup
from django.conf import settings
from django.core.management.commands.migrate import Command as migrate


def pytest_configure():
    test_settings = dict(
        INSTALLED_APPS=[
            'django.contrib.admin',
            'django.contrib.sessions',
            'django.contrib.messages',
            'raven.contrib.django.raven_compat',
            'rest_framework',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.staticfiles',
        ],
        DATABASES={'default': dict(
            ENGINE='django.db.backends.sqlite3',
            NAME=os.path.join(os.path.curdir, 'd.sqlite'),
            OPTIONS={},
            CONN_MAX_AGE=0,
            TEST={'NAME': 't.db'}
        )}
    )
    settings.configure(**test_settings)
    setup()
    migrate().handle(verbosity=1, interactive=False, database='default', run_syncdb=False, app_label=None, plan=True)

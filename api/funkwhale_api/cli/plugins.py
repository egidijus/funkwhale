import os
import subprocess
import sys

import click
from django.conf import settings


from . import base


@base.cli.group()
def plugins():
    """Manage plugins"""
    pass


@plugins.command("install")
@click.argument("plugin", nargs=-1)
def install(plugin):
    """
    Install a plugin from a given URL (zip, pip or git are supported)
    """
    if not plugin:
        return click.echo("No plugin provided")

    click.echo("Installing plugins…")
    pip_install(list(plugin), settings.FUNKWHALE_PLUGINS_PATH)


def pip_install(deps, target):
    if not deps:
        return
    pip_path = os.path.join(os.path.dirname(sys.executable), "pip")
    subprocess.check_call([pip_path, "install", "-t", target] + deps)

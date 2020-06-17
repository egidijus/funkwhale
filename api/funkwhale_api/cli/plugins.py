import os
import subprocess

import click

from django.conf import settings

from . import base


@base.cli.group()
def plugins():
    """Install, configure and remove plugins"""
    pass


@plugins.command("install")
@click.argument("name_or_url", nargs=-1)
@click.option("--builtins", is_flag=True)
@click.option("--pip-args")
def install(name_or_url, builtins, pip_args):
    """
    Installed the specified plug using their name.

    If --builtins is provided, it will also install
    plugins present at FUNKWHALE_PLUGINS_PATH
    """
    pip_args = pip_args or ""
    target_path = settings.FUNKWHALE_PLUGINS_PATH
    builtins_path = os.path.join(settings.APPS_DIR, "plugins")
    builtins_plugins = [f.path for f in os.scandir(builtins_path) if f.is_dir()]
    command = "pip install {} --target={} {}".format(
        pip_args, target_path, " ".join(builtins_plugins)
    )
    subprocess.run(
        command, shell=True, check=True,
    )

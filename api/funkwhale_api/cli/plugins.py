import os
import shutil
import subprocess
import sys
import tempfile

import click

from django.conf import settings

from . import base


PIP = os.path.join(sys.prefix, "bin", "pip")


@base.cli.group()
def plugins():
    """Install, configure and remove plugins"""
    pass


def get_all_plugins():
    plugins = [
        f.path
        for f in os.scandir(settings.FUNKWHALE_PLUGINS_PATH)
        if "/funkwhale_plugin_" in f.path
    ]
    plugins = [
        p.split("-")[0].split("/")[-1].replace("funkwhale_plugin_", "") for p in plugins
    ]
    return plugins


@plugins.command("install")
@click.argument("name_or_url", nargs=-1)
@click.option("--builtins", is_flag=True)
@click.option("--pip-args")
def install(name_or_url, builtins, pip_args):
    """
    Installed the specified plug using their name.
    """
    pip_args = pip_args or ""
    all_plugins = []
    for p in name_or_url:
        builtin_path = os.path.join(
            settings.APPS_DIR, "plugins", "funkwhale_plugin_{}".format(p)
        )
        if os.path.exists(builtin_path):
            all_plugins.append(builtin_path)
        else:
            all_plugins.append(p)
    install_plugins(pip_args, all_plugins)
    click.echo(
        "Installation completed, ensure FUNKWHALE_PLUGINS={} is present in your .env file".format(
            ",".join(get_all_plugins())
        )
    )


def install_plugins(pip_args, all_plugins):
    with tempfile.TemporaryDirectory() as tmpdirname:
        command = "{} install {} --target {} --build={} {}".format(
            PIP,
            pip_args,
            settings.FUNKWHALE_PLUGINS_PATH,
            tmpdirname,
            " ".join(all_plugins),
        )
        subprocess.run(
            command, shell=True, check=True,
        )


@plugins.command("uninstall")
@click.argument("name", nargs=-1)
def uninstall(name):
    """
    Remove plugins
    """
    to_remove = ["funkwhale_plugin_{}".format(n) for n in name]
    command = "{} uninstall -y {}".format(PIP, " ".join(to_remove))
    subprocess.run(
        command, shell=True, check=True,
    )
    for f in os.scandir(settings.FUNKWHALE_PLUGINS_PATH):
        for n in name:
            if "/funkwhale_plugin_{}".format(n) in f.path:
                shutil.rmtree(f.path)
    click.echo(
        "Removal completed, set FUNKWHALE_PLUGINS={} in your .env file".format(
            ",".join(get_all_plugins())
        )
    )

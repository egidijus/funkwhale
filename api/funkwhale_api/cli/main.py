import click
import sys

from . import base
from . import library  # noqa
from . import media  # noqa
from . import users  # noqa

from rest_framework.exceptions import ValidationError


def invoke():
    try:
        return base.cli()
    except ValidationError as e:
        click.secho("Invalid data:", fg="red")
        for field, errors in e.detail.items():
            click.secho("  {}:".format(field), fg="red")
            for error in errors:
                click.secho("    - {}".format(error), fg="red")
        sys.exit(1)

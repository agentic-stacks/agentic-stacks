"""Agentic Stacks CLI."""

import click
import agentic_stacks

from agentic_stacks_cli.commands.init import init
from agentic_stacks_cli.commands.doctor import doctor
from agentic_stacks_cli.commands.validate import validate
from agentic_stacks_cli.commands.login import login
from agentic_stacks_cli.commands.publish import publish
from agentic_stacks_cli.commands.pull import pull
from agentic_stacks_cli.commands.search import search
from agentic_stacks_cli.commands.upgrade import upgrade
from agentic_stacks_cli.commands.create import create
from agentic_stacks_cli.commands.list import list_stacks
from agentic_stacks_cli.commands.remove import remove


@click.group()
@click.version_option(version=agentic_stacks.__version__, prog_name="agentic-stacks")
def cli():
    """Agentic Stacks CLI — manage composed domain expertise."""
    pass


cli.add_command(init)
cli.add_command(create)
cli.add_command(doctor)
cli.add_command(validate)
cli.add_command(login)
cli.add_command(publish)
cli.add_command(pull)
cli.add_command(search)
cli.add_command(list_stacks)
cli.add_command(remove)
cli.add_command(upgrade)


def main():
    cli()

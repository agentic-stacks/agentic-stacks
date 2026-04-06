"""Agentic Stacks CLI."""

import click
import agentic_stacks

from agentic_stacks_cli.commands.init import init
from agentic_stacks_cli.commands.doctor import doctor
from agentic_stacks_cli.commands.login import login
from agentic_stacks_cli.commands.publish import publish
from agentic_stacks_cli.commands.pull import pull
from agentic_stacks_cli.commands.search import search
from agentic_stacks_cli.commands.create import create
from agentic_stacks_cli.commands.list import list_stacks
from agentic_stacks_cli.commands.remove import remove
from agentic_stacks_cli.commands.update import update
from agentic_stacks_cli.commands.lint import lint
from agentic_stacks_cli.commands.explain import explain


@click.group()
@click.version_option(version=agentic_stacks.__version__, prog_name="agentic-stacks")
def cli():
    """Agentic Stacks CLI — manage composed domain expertise."""
    pass


cli.add_command(init)
cli.add_command(create)
cli.add_command(doctor)
cli.add_command(login)
cli.add_command(publish)
cli.add_command(pull)
cli.add_command(search)
cli.add_command(list_stacks)
cli.add_command(remove)
cli.add_command(update)
cli.add_command(lint)
cli.add_command(explain)


def main():
    cli()

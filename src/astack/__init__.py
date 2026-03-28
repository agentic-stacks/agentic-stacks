"""astack — CLI for Agentic Stacks."""

import click
import agentic_stacks

from astack.commands.init import init


@click.group()
@click.version_option(version=agentic_stacks.__version__, prog_name="astack")
def cli():
    """Agentic Stacks CLI — manage composed domain expertise."""
    pass


cli.add_command(init)


def main():
    cli()

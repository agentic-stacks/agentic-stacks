"""astack — CLI for Agentic Stacks."""

import click
import agentic_stacks


@click.group()
@click.version_option(version=agentic_stacks.__version__, prog_name="astack")
def cli():
    """Agentic Stacks CLI — manage composed domain expertise."""
    pass


def main():
    cli()

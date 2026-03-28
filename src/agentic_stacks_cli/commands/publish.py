"""agentic-stacks publish — package and push a stack to the registry."""

import pathlib
import tempfile

import click

from agentic_stacks.manifest import load_manifest, ManifestError
from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.oci import package_stack, push_stack
from agentic_stacks_cli.api_client import RegistryClient


@click.command()
@click.option("--path", type=click.Path(exists=True), default=".", help="Path to stack directory")
@click.option("--config", "config_path", default=None, type=click.Path(), help="Config file path")
def publish(path: str, config_path: str | None):
    """Package and publish a stack to the registry."""
    stack_dir = pathlib.Path(path)
    cfg_path = pathlib.Path(config_path) if config_path else None
    cfg = load_config(cfg_path)

    token = cfg.get("token")
    if not token:
        raise click.ClickException("Not authenticated. Run 'agentic-stacks login' first.")

    try:
        manifest = load_manifest(stack_dir / "stack.yaml")
    except ManifestError as e:
        raise click.ClickException(f"Invalid stack: {e}")

    name = manifest["name"]
    namespace = manifest["namespace"]
    version = manifest["version"]
    registry = cfg.get("registry", "ghcr.io")

    click.echo(f"Publishing {namespace}/{name}@{version}...")

    with tempfile.TemporaryDirectory() as tmp:
        click.echo("  Packaging...")
        tarball = package_stack(stack_dir, pathlib.Path(tmp))

        annotations = {
            "dev.agentic-stacks.name": name,
            "dev.agentic-stacks.namespace": namespace,
            "dev.agentic-stacks.version": version,
            "dev.agentic-stacks.description": manifest.get("description", ""),
        }
        skills = manifest.get("skills", [])
        if skills:
            annotations["dev.agentic-stacks.skills"] = ",".join(s["name"] for s in skills)
        target = manifest.get("target", {})
        if target.get("software"):
            annotations["dev.agentic-stacks.target-software"] = target["software"]
        if target.get("versions"):
            annotations["dev.agentic-stacks.target-versions"] = ",".join(str(v) for v in target["versions"])

        click.echo(f"  Pushing to {registry}/{namespace}/{name}:{version}...")
        ref, digest = push_stack(tarball_path=tarball, registry=registry, namespace=namespace,
                                  name=name, version=version, annotations=annotations)

    click.echo(f"  Pushed: {ref}")
    click.echo(f"  Digest: {digest}")

    api_url = cfg.get("api_url", "https://agentic-stacks.com/api/v1")
    client = RegistryClient(api_url=api_url, token=token)
    try:
        client.register_stack({
            "namespace": namespace, "name": name, "version": version,
            "description": manifest.get("description", ""),
            "target": manifest.get("target", {}),
            "skills": manifest.get("skills", []),
            "profiles": manifest.get("profiles", {}),
            "depends_on": manifest.get("depends_on", []),
            "deprecations": manifest.get("deprecations", []),
            "requires": manifest.get("requires", {}),
            "digest": digest, "registry_ref": ref,
        })
        click.echo("  Registered with registry.")
    except Exception as e:
        click.echo(f"  Warning: Could not register with registry: {e}")

    click.echo(f"\nPublished {namespace}/{name}@{version}")

"""Stack manifest (stack.yaml) parsing and validation."""

import pathlib
import yaml


REQUIRED_FIELDS = ["name", "version", "description"]


class ManifestError(Exception):
    """Raised when a stack manifest is invalid or missing."""
    pass


def load_manifest(path: pathlib.Path) -> dict:
    """Load and validate a stack.yaml manifest file.

    Args:
        path: Path to stack.yaml file.

    Returns:
        Parsed manifest dict with computed 'full_name' field added.

    Raises:
        ManifestError: If the file is missing or has invalid content.
    """
    path = pathlib.Path(path)
    if not path.exists():
        raise ManifestError(f"Manifest not found: {path}")

    try:
        text = path.read_text()
        manifest = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise ManifestError(f"Invalid YAML in {path}: {e}")

    if not isinstance(manifest, dict):
        raise ManifestError(f"Manifest must be a YAML mapping, got {type(manifest).__name__}")

    missing = [f for f in REQUIRED_FIELDS if f not in manifest]
    if missing:
        raise ManifestError(
            f"Manifest {path} missing required fields: {', '.join(missing)}"
        )

    # owner field: prefer 'owner', fall back to 'namespace' for backwards compat
    if "owner" not in manifest:
        if "namespace" in manifest:
            manifest["owner"] = manifest["namespace"]
        else:
            raise ManifestError(
                f"Manifest {path} missing required field: owner "
                f"(or 'namespace' for backwards compatibility)"
            )

    # Keep namespace in sync for any code that still reads it
    manifest["namespace"] = manifest["owner"]

    manifest.setdefault("skills", [])
    manifest.setdefault("profiles", {"categories": [], "path": "profiles/"})
    manifest.setdefault("depends_on", [])
    manifest.setdefault("deprecations", [])
    manifest.setdefault("requires", {})
    manifest.setdefault("target", {"software": "", "versions": []})
    manifest.setdefault("project", {})
    manifest.setdefault("repository", "")
    manifest.setdefault("docs_sources", [])
    if "extends" not in manifest:
        manifest["extends"] = None

    manifest["full_name"] = f"{manifest['owner']}/{manifest['name']}"

    return manifest

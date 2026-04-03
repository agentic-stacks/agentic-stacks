"""Agentic Stacks — thin runtime for composed domain expertise."""

__version__ = "0.1.4"

from agentic_stacks.manifest import load_manifest, ManifestError
from agentic_stacks.profiles import (
    load_profile,
    load_profiles_by_category,
    merge_profiles,
    EnforcedKeyError,
)
from agentic_stacks.environments import (
    load_environment,
    list_environments,
    create_environment,
    validate_environment,
    StackEnvironmentError,
)
from agentic_stacks.schema import validate_against_schema, ValidationError

__all__ = [
    "load_manifest",
    "ManifestError",
    "load_profile",
    "load_profiles_by_category",
    "merge_profiles",
    "EnforcedKeyError",
    "load_environment",
    "list_environments",
    "create_environment",
    "validate_environment",
    "StackEnvironmentError",
    "validate_against_schema",
    "ValidationError",
]

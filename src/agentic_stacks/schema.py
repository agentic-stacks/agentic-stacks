"""JSON Schema validation utilities."""

import jsonschema


class ValidationError(Exception):
    """Raised when data fails schema validation."""

    def __init__(self, message: str, errors: list[str]):
        self.errors = errors
        super().__init__(message)


def validate_against_schema(data: dict, schema: dict) -> None:
    """Validate data against a JSON Schema. Raises ValidationError on failure."""
    validator = jsonschema.Draft7Validator(schema)
    errors = list(validator.iter_errors(data))
    if errors:
        messages = []
        for error in errors:
            path = ".".join(str(p) for p in error.absolute_path)
            prefix = f"{path}: " if path else ""
            messages.append(f"{prefix}{error.message}")
        raise ValidationError(
            f"Validation failed with {len(errors)} error(s):\n"
            + "\n".join(f"  - {m}" for m in messages),
            errors=messages,
        )

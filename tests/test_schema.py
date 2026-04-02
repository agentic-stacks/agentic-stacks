import json
import pytest
from agentic_stacks.schema import validate_against_schema, ValidationError


def test_valid_data_passes(sample_stack_path):
    schema_path = sample_stack_path / "environments" / "_schema.json"
    schema = json.loads(schema_path.read_text())
    data = {
        "name": "dev",
        "profiles": {
            "security": "baseline",
            "networking": "option-a",
            "storage": "default",
        },
    }
    validate_against_schema(data, schema)


def test_missing_required_field_raises(sample_stack_path):
    schema_path = sample_stack_path / "environments" / "_schema.json"
    schema = json.loads(schema_path.read_text())
    data = {"name": "dev"}
    with pytest.raises(ValidationError, match="profiles"):
        validate_against_schema(data, schema)


def test_invalid_enum_value_raises(sample_stack_path):
    schema_path = sample_stack_path / "environments" / "_schema.json"
    schema = json.loads(schema_path.read_text())
    data = {
        "name": "dev",
        "profiles": {
            "security": "baseline",
            "networking": "option-a",
            "storage": "default",
        },
        "approval": {"tier": "invalid-tier"},
    }
    with pytest.raises(ValidationError, match="invalid-tier"):
        validate_against_schema(data, schema)

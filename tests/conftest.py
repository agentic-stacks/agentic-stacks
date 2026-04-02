import pathlib
import pytest

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_stack_path():
    return FIXTURES_DIR / "sample-stack"


@pytest.fixture
def sample_profiles_path(sample_stack_path):
    return sample_stack_path / "profiles"


@pytest.fixture
def sample_environments_path(sample_stack_path):
    return sample_stack_path / "environments"

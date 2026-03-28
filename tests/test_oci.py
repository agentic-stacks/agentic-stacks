import tarfile
from unittest.mock import patch, MagicMock
from agentic_stacks_cli.oci import package_stack, push_stack, pull_stack, EXCLUDE_PATTERNS


def test_package_stack_creates_tarball(tmp_path):
    stack_dir = tmp_path / "my-stack"
    stack_dir.mkdir()
    (stack_dir / "stack.yaml").write_text("name: test\n")
    (stack_dir / "skills").mkdir()
    (stack_dir / "skills" / "deploy.md").write_text("# Deploy\n")
    (stack_dir / ".git").mkdir()
    (stack_dir / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    (stack_dir / ".venv").mkdir()
    (stack_dir / "__pycache__").mkdir()

    output = tmp_path / "output"
    output.mkdir()
    tarball_path = package_stack(stack_dir, output)

    assert tarball_path.exists()
    assert tarball_path.suffix == ".gz"

    with tarfile.open(tarball_path, "r:gz") as tar:
        names = tar.getnames()
        assert "stack.yaml" in names
        assert "skills/deploy.md" in names
        assert not any(".git" in n for n in names)
        assert not any(".venv" in n for n in names)
        assert not any("__pycache__" in n for n in names)


def test_push_stack_calls_oras(tmp_path):
    tarball = tmp_path / "test-1.0.0.tar.gz"
    tarball.write_bytes(b"fake tarball")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Digest: sha256:abc123\n")
        ref, digest = push_stack(tarball_path=tarball, registry="ghcr.io",
                                  namespace="agentic-stacks", name="test", version="1.0.0",
                                  annotations={"dev.agentic-stacks.name": "test"})

    assert ref == "ghcr.io/agentic-stacks/test:1.0.0"
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "oras" in cmd[0]
    assert "push" in cmd


def test_pull_stack_calls_oras(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Digest: sha256:def456\n")
        pull_stack(registry="ghcr.io", namespace="agentic-stacks", name="test",
                   version="1.0.0", output_dir=tmp_path / "output")

    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "oras" in cmd[0]
    assert "pull" in cmd


def test_exclude_patterns():
    assert ".git" in EXCLUDE_PATTERNS
    assert ".venv" in EXCLUDE_PATTERNS
    assert "__pycache__" in EXCLUDE_PATTERNS
    assert "state" in EXCLUDE_PATTERNS
    assert ".superpowers" in EXCLUDE_PATTERNS

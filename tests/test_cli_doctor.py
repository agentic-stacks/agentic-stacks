import json
import yaml
from click.testing import CliRunner
from astack import cli


def _create_valid_stack(path):
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "test", "namespace": "testorg", "version": "1.0.0", "description": "Test stack",
        "skills": [{"name": "deploy", "entry": "skills/deploy/", "description": "Deploy"}],
        "profiles": {"categories": ["security"], "path": "profiles/"},
        "environment_schema": "environments/_schema.json",
        "depends_on": [], "deprecations": [],
    }
    (path / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))
    (path / "skills").mkdir(exist_ok=True)
    (path / "skills" / "deploy").mkdir(exist_ok=True)
    (path / "profiles").mkdir(exist_ok=True)
    (path / "profiles" / "security").mkdir(exist_ok=True)
    (path / "environments").mkdir(exist_ok=True)
    (path / "environments" / "_schema.json").write_text(json.dumps({"type": "object", "required": ["name"]}))


def test_doctor_valid_stack(tmp_path):
    _create_valid_stack(tmp_path / "stack")
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(tmp_path / "stack")])
    assert result.exit_code == 0
    assert "healthy" in result.output.lower()


def test_doctor_missing_manifest(tmp_path):
    (tmp_path / "stack").mkdir()
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(tmp_path / "stack")])
    assert result.exit_code != 0


def test_doctor_invalid_manifest(tmp_path):
    (tmp_path / "stack").mkdir()
    (tmp_path / "stack" / "stack.yaml").write_text("just: a string value\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(tmp_path / "stack")])
    assert result.exit_code != 0


def test_doctor_missing_skills_dir(tmp_path):
    _create_valid_stack(tmp_path / "stack")
    import shutil
    shutil.rmtree(tmp_path / "stack" / "skills")
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(tmp_path / "stack")])
    assert "missing" in result.output.lower() or "warn" in result.output.lower() or "skills" in result.output.lower()


def test_doctor_deprecated_skills_warning(tmp_path):
    _create_valid_stack(tmp_path / "stack")
    manifest = yaml.safe_load((tmp_path / "stack" / "stack.yaml").read_text())
    manifest["deprecations"] = [{"skill": "old-deploy", "since": "0.9.0", "removal": "2.0.0", "replacement": "deploy", "reason": "Replaced"}]
    (tmp_path / "stack" / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(tmp_path / "stack")])
    assert "deprecat" in result.output.lower()


def test_doctor_defaults_to_cwd(tmp_path, monkeypatch):
    _create_valid_stack(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0

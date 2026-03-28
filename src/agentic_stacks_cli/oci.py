"""OCI packaging and push/pull via oras CLI."""

import pathlib
import subprocess
import tarfile

EXCLUDE_PATTERNS = {
    ".git", ".venv", "__pycache__", "state", ".superpowers",
    ".pytest_cache", "dist", ".coverage",
}

MEDIA_TYPE = "application/vnd.agentic-stacks.stack.v1+tar+gzip"


def _should_exclude(path: pathlib.Path) -> bool:
    parts = path.parts
    for part in parts:
        if part in EXCLUDE_PATTERNS:
            return True
        if part.endswith(".egg-info"):
            return True
        if part.endswith(".pyc"):
            return True
    return False


def package_stack(stack_dir: pathlib.Path, output_dir: pathlib.Path) -> pathlib.Path:
    stack_dir = pathlib.Path(stack_dir)
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tarball_path = output_dir / f"{stack_dir.name}.tar.gz"
    with tarfile.open(tarball_path, "w:gz") as tar:
        for item in sorted(stack_dir.rglob("*")):
            rel = item.relative_to(stack_dir)
            if _should_exclude(rel):
                continue
            tar.add(item, arcname=str(rel))
    return tarball_path


def push_stack(tarball_path: pathlib.Path, registry: str, namespace: str,
               name: str, version: str, annotations: dict[str, str] | None = None) -> tuple[str, str]:
    ref = f"{registry}/{namespace}/{name}:{version}"
    cmd = ["oras", "push", ref, str(tarball_path), "--artifact-type", MEDIA_TYPE]
    if annotations:
        for key, value in annotations.items():
            cmd.extend(["--annotation", f"{key}={value}"])
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"oras push failed: {result.stderr}")
    digest = ""
    for line in result.stdout.splitlines():
        if line.startswith("Digest:"):
            digest = line.split(":", 1)[1].strip()
            break
    return ref, digest


def pull_stack(registry: str, namespace: str, name: str, version: str,
               output_dir: pathlib.Path) -> str:
    ref = f"{registry}/{namespace}/{name}:{version}"
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["oras", "pull", ref, "--output", str(output_dir)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"oras pull failed: {result.stderr}")
    digest = ""
    for line in result.stdout.splitlines():
        if line.startswith("Digest:"):
            digest = line.split(":", 1)[1].strip()
            break
    return digest

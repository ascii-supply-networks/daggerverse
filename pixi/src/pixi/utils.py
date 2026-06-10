"""Pure helpers for the Pixi Dagger module."""

import posixpath
import re
import tomllib
from pathlib import PurePosixPath

from packaging.specifiers import SpecifierSet
from packaging.version import Version

_DEFAULT_IMAGE = "ghcr.io/prefix-dev/pixi"
_DEFAULT_VERSION = "0.70.2"
_VERSION_SPECIFIER_RE = re.compile(r"[><=!~]")


def image_ref(version: str) -> str:
    """Return the Pixi container image reference for a version tag."""
    return f"{_DEFAULT_IMAGE}:{version}"


def workspace_path(lockfile: str) -> str:
    """Source-relative directory holding the given pixi.lock."""
    return posixpath.dirname(lockfile) or "."


def is_excluded(path: str, patterns: list[str]) -> bool:
    """Whether a workspace path matches any exclude glob pattern."""
    workspace = PurePosixPath(path)
    return any(workspace.full_match(pattern) for pattern in patterns)


def is_exact_version(value: str) -> bool:
    stripped = value.strip()
    if stripped.startswith("=="):
        return "*" not in stripped
    return not _VERSION_SPECIFIER_RE.search(stripped)


def normalize_exact_version(value: str) -> str:
    if value.startswith("=="):
        return value[2:].strip()
    return value.strip()


def minimal_compatible_version(specifier: str) -> str | None:
    """Lowest version satisfying a PEP 440 specifier, computed from the specifier itself."""
    spec = SpecifierSet(specifier)
    candidates: list[Version] = []
    for clause in spec:
        if clause.operator in (">=", "~=", "=="):
            base = clause.version[:-2] if clause.version.endswith(".*") else clause.version
            candidates.append(Version(base))
        elif clause.operator == ">":
            release = Version(clause.version).release
            candidates.append(Version(".".join(str(n) for n in (*release[:-1], release[-1] + 1))))
    feasible = sorted(candidate for candidate in candidates if candidate in spec)
    if not feasible:
        return None
    return str(feasible[0])


def resolve_specifier(value: str) -> str:
    """Concrete Pixi image tag for a configured version value."""
    if is_exact_version(value):
        return normalize_exact_version(value)
    return minimal_compatible_version(value) or _DEFAULT_VERSION


def parse_manifest(content: str, manifest_name: str) -> dict:
    """Parse a Pixi manifest and return the native Pixi manifest table."""
    data = tomllib.loads(content)
    if manifest_name == "pyproject.toml":
        return data.get("tool", {}).get("pixi", {})
    return data


def parse_requires_pixi(content: str, manifest_name: str) -> str | None:
    """Return `requires-pixi` from a Pixi manifest, if present."""
    manifest = parse_manifest(content, manifest_name)
    workspace = manifest.get("workspace", {})
    value = workspace.get("requires-pixi")
    if isinstance(value, str):
        return value
    return None


def parse_environments(content: str, manifest_name: str) -> list[str]:
    """Return all named Pixi environments declared by a manifest, including `default`."""
    manifest = parse_manifest(content, manifest_name)
    environments = manifest.get("environments", {})
    names = {"default"}
    if isinstance(environments, dict):
        names.update(str(name) for name in environments)
    return sorted(names)


def build_pixi_install_args(environment: str) -> list[str]:
    """Build the `pixi install` argv used by the module."""
    return ["pixi", "install", "--locked", "--environment", environment]


def build_pixi_lock_check_args() -> list[str]:
    """Build the `pixi lock` argv used by the module."""
    return ["pixi", "lock", "--check"]


def build_pixi_run_args(command: list[str], environment: str) -> list[str]:
    """Build the `pixi run` argv used by the module."""
    if not command:
        msg = "Pixi run requires at least one command argument."
        raise ValueError(msg)
    return ["pixi", "run", "--locked", "--environment", environment, *command]


def build_pixi_shell_hook_args(environment: str, *, json: bool = True) -> list[str]:
    """Build the `pixi shell-hook` argv used by the module."""
    args = ["pixi", "shell-hook", "--locked", "--environment", environment]
    if json:
        args.append("--json")
    return args

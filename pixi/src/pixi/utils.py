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


def normalize_environments(environments: list[str]) -> list[str]:
    """Return unique environment names in input order."""
    names: list[str] = []
    for environment in environments:
        name = environment.strip()
        if not name:
            msg = "Pixi environment names must not be empty."
            raise ValueError(msg)
        if name not in names:
            names.append(name)
    if not names:
        msg = "At least one Pixi environment is required."
        raise ValueError(msg)
    return names


def normalize_runtime_source_paths(paths: list[str] | None) -> list[str] | None:
    """Return runtime source include paths in input order."""
    if paths is None:
        return None

    normalized: list[str] = []
    seen: set[str] = set()
    for path in paths:
        value = path.strip()
        if not value:
            msg = "Runtime source paths must not be empty."
            raise ValueError(msg)
        value = value.removeprefix("./")
        if value == ".":
            return None
        if value.startswith("/"):
            msg = f"Runtime source path {path!r} must be relative to the source root."
            raise ValueError(msg)
        if ".." in PurePosixPath(value).parts:
            msg = f"Runtime source path {path!r} must not contain '..'."
            raise ValueError(msg)
        if value not in seen:
            normalized.append(value)
            seen.add(value)
    return normalized


def build_pixi_install_args(environment: str) -> list[str]:
    """Build the `pixi install` argv used by the module."""
    if not environment.strip():
        msg = "Pixi environment name must not be empty."
        raise ValueError(msg)
    return ["pixi", "install", "--locked", "--environment", environment]


def build_pixi_install_all_args() -> list[str]:
    """Build the `pixi install --all` argv used by the module."""
    return ["pixi", "install", "--locked", "--all"]


def build_pixi_lock_check_args() -> list[str]:
    """Build the `pixi lock` argv used by the module."""
    return ["pixi", "lock", "--check"]


def build_pixi_run_args(command: list[str], environment: str) -> list[str]:
    """Build the `pixi run` argv used by the module."""
    if not command:
        msg = "Pixi run requires at least one command argument."
        raise ValueError(msg)
    return ["pixi", "run", "--locked", "--environment", environment, *command]


def build_pixi_shell_hook_args(environment: str, *, json: bool = True, shell: str | None = None) -> list[str]:
    """Build the `pixi shell-hook` argv used by the module."""
    args = ["pixi", "shell-hook", "--locked", "--environment", environment]
    if shell is not None:
        args.extend(["--shell", shell])
    if json:
        args.append("--json")
    return args


def build_bash_entrypoint(shell_hook: str) -> str:
    """Build a Bash entrypoint that activates a Pixi environment without Pixi."""
    return f'#!/usr/bin/env bash\nset -euo pipefail\n{shell_hook.rstrip()}\nexec "$@"\n'

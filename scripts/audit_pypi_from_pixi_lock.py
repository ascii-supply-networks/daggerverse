"""Audit PyPI packages recorded in a pixi.lock file with pip-audit."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path

import yaml
from packaging.version import InvalidVersion, Version

_NON_PYPI_PREFIXES = (".", "./", "../", "file://", "git+")
_PYPI_HOST_MARKERS = ("files.pythonhosted.org", "pypi.org")


def _normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _is_pypi_source(source: str) -> bool:
    if source.startswith(_NON_PYPI_PREFIXES):
        return False
    return any(marker in source for marker in _PYPI_HOST_MARKERS)


def _version_key(version: str) -> Version:
    try:
        return Version(version)
    except InvalidVersion:
        return Version("0")


def _extract_requirements(lockfile: Path) -> tuple[list[list[str]], list[str]]:
    data = yaml.safe_load(lockfile.read_text(encoding="utf-8"))
    packages = data.get("packages", []) if isinstance(data, dict) else []
    versions_by_name: dict[str, dict[str, str]] = {}
    skipped: list[str] = []

    for package in packages:
        if not isinstance(package, dict):
            continue
        source = package.get("pypi")
        name = package.get("name")
        version = package.get("version")
        if source is None or name is None or version is None:
            continue
        source = str(source)
        name = str(name)
        version = str(version)
        normalized = _normalize_name(name)
        if not _is_pypi_source(source):
            skipped.append(f"{normalized} ({source})")
            continue
        versions_by_name.setdefault(normalized, {})[version] = name

    if not versions_by_name:
        return [], sorted(set(skipped))

    sorted_versions = {
        name: sorted(versions.items(), key=lambda item: _version_key(item[0]))
        for name, versions in versions_by_name.items()
    }
    max_versions = max(len(versions) for versions in sorted_versions.values())
    passes: list[list[str]] = []
    for index in range(max_versions):
        requirements = []
        for package_name in sorted(sorted_versions):
            versions = sorted_versions[package_name]
            if index >= len(versions):
                continue
            version, display_name = versions[index]
            requirements.append(f"{display_name}=={version}")
        if requirements:
            passes.append(requirements)

    return passes, sorted(set(skipped))


def _write_requirements(requirements: Iterable[str]) -> Path:
    fd, raw_path = tempfile.mkstemp(prefix="pixi-pypi-audit-", suffix=".txt")
    path = Path(raw_path)
    with open(fd, "w", encoding="utf-8") as handle:
        handle.write("\n".join(requirements))
        handle.write("\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lockfile", type=Path, default=Path("pixi.lock"))
    args = parser.parse_args()

    if not args.lockfile.exists():
        print(f"{args.lockfile} does not exist", file=sys.stderr)
        return 1

    requirement_passes, skipped = _extract_requirements(args.lockfile)
    print(f"Found {sum(len(requirements) for requirements in requirement_passes)} PyPI package version(s).", flush=True)
    if skipped:
        print(f"Skipped {len(skipped)} non-PyPI package source(s):", flush=True)
        for entry in skipped:
            print(f"  - {entry}", flush=True)

    worst_returncode = 0
    with tempfile.TemporaryDirectory(prefix="pixi-pypi-audit-cache-") as cache_dir:
        for index, requirements in enumerate(requirement_passes, start=1):
            path = _write_requirements(requirements)
            try:
                print(f"Audit pass {index}: {len(requirements)} package(s)", flush=True)
                result = subprocess.run(
                    [
                        "pip-audit",
                        "-r",
                        str(path),
                        "--desc",
                        "--progress-spinner=off",
                        "--cache-dir",
                        cache_dir,
                        "--no-deps",
                        "--disable-pip",
                    ],
                    check=False,
                )
                worst_returncode = max(worst_returncode, result.returncode)
            finally:
                path.unlink(missing_ok=True)

    return worst_returncode


if __name__ == "__main__":
    raise SystemExit(main())

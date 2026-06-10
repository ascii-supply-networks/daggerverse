"""Download the pinned Dagger CLI and run it."""

import argparse
import hashlib
import os
import platform
import shutil
import stat
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path
from urllib.request import urlopen

DEFAULT_DAGGER_VERSION = "0.21.4"
RELEASE_BASE_URL = "https://github.com/dagger/dagger/releases/download"


def _target() -> tuple[str, str, str]:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":
        os_name = "darwin"
        extension = ".tar.gz"
    elif system == "linux":
        os_name = "linux"
        extension = ".tar.gz"
    elif system == "windows":
        os_name = "windows"
        extension = ".zip"
    else:
        raise RuntimeError(f"Unsupported operating system: {platform.system()}")

    if machine in {"x86_64", "amd64"}:
        arch = "amd64"
    elif machine in {"aarch64", "arm64"}:
        arch = "arm64"
    elif machine in {"armv7l", "armv7"}:
        arch = "armv7"
    else:
        raise RuntimeError(f"Unsupported architecture: {platform.machine()}")

    return os_name, arch, extension


def _download(url: str, destination: Path) -> None:
    with urlopen(url, timeout=60) as response:
        destination.write_bytes(response.read())


def _checksums(version: str) -> dict[str, str]:
    raw_version = version if version.startswith("v") else f"v{version}"
    url = f"{RELEASE_BASE_URL}/{raw_version}/checksums.txt"
    with urlopen(url, timeout=60) as response:
        lines = response.read().decode("utf-8").splitlines()

    checksums: dict[str, str] = {}
    for line in lines:
        if not line.strip():
            continue
        checksum, filename = line.split(maxsplit=1)
        checksums[filename] = checksum
    return checksums


def _verify(path: Path, expected_sha256: str) -> None:
    actual_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual_sha256 != expected_sha256:
        raise RuntimeError(f"Checksum mismatch for {path.name}: expected {expected_sha256}, got {actual_sha256}")


def _extract(archive: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as handle:
            handle.extractall(destination)
    else:
        with tarfile.open(archive) as handle:
            handle.extractall(destination, filter="data")

    executable = destination / ("dagger.exe" if platform.system().lower() == "windows" else "dagger")
    if not executable.exists():
        matches = list(destination.rglob(executable.name))
        if not matches:
            raise RuntimeError(f"Could not find {executable.name} in {archive.name}")
        executable = matches[0]

    executable.chmod(executable.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return executable


def _dagger_binary(version: str, cache_dir: Path) -> Path:
    raw_version = version if version.startswith("v") else f"v{version}"
    os_name, arch, extension = _target()
    filename = f"dagger_{raw_version}_{os_name}_{arch}{extension}"
    binary_dir = cache_dir / raw_version / f"{os_name}_{arch}"
    executable = binary_dir / ("dagger.exe" if os_name == "windows" else "dagger")
    if executable.exists():
        return executable

    checksums = _checksums(raw_version)
    if filename not in checksums:
        raise RuntimeError(f"No checksum entry for {filename}")

    url = f"{RELEASE_BASE_URL}/{raw_version}/{filename}"
    with tempfile.TemporaryDirectory(prefix="dagger-cli-") as tempdir:
        archive = Path(tempdir) / filename
        _download(url, archive)
        _verify(archive, checksums[filename])
        extracted = _extract(archive, binary_dir)

    if extracted != executable:
        executable.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(extracted), executable)
    return executable


def main() -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--dagger-version", default=os.environ.get("DAGGER_VERSION", DEFAULT_DAGGER_VERSION))
    parser.add_argument("--cache-dir", type=Path, default=Path(".pixi") / "dagger-cli")
    args, dagger_args = parser.parse_known_args()

    executable = _dagger_binary(args.dagger_version, args.cache_dir)
    command = [str(executable), *dagger_args]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())

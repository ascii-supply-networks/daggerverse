import pytest

from pixi.utils import (
    build_bash_entrypoint,
    build_pixi_install_all_args,
    build_pixi_install_args,
    build_pixi_lock_check_args,
    build_pixi_run_args,
    build_pixi_shell_hook_args,
    image_ref,
    is_excluded,
    normalize_environments,
    normalize_runtime_source_paths,
    parse_environments,
    parse_requires_pixi,
    resolve_specifier,
    workspace_path,
)


def test_image_ref() -> None:
    assert image_ref("0.70.2") == "ghcr.io/prefix-dev/pixi:0.70.2"


def test_workspace_path() -> None:
    assert workspace_path("pixi.lock") == "."
    assert workspace_path("sub/project/pixi.lock") == "sub/project"


def test_exclude_patterns() -> None:
    assert is_excluded("tests/_packages/clean", ["**/tests/_packages/**"])
    assert not is_excluded("src/app", ["**/tests/_packages/**"])


def test_resolve_exact_requires_pixi() -> None:
    assert resolve_specifier("==0.70.1") == "0.70.1"
    assert resolve_specifier("0.70.2") == "0.70.2"


def test_resolve_range_requires_pixi() -> None:
    assert resolve_specifier(">=0.70.0,<0.71") == "0.70.0"


def test_resolve_upper_bound_only_falls_back_to_default() -> None:
    assert resolve_specifier("<0.71") == "0.70.2"


def test_parse_requires_pixi_from_pixi_toml() -> None:
    content = """
[workspace]
name = "demo"
requires-pixi = ">=0.70.0"
"""
    assert parse_requires_pixi(content, "pixi.toml") == ">=0.70.0"


def test_parse_requires_pixi_from_pyproject() -> None:
    content = """
[project]
name = "demo"
version = "0.1.0"

[tool.pixi.workspace]
requires-pixi = "==0.70.1"
"""
    assert parse_requires_pixi(content, "pyproject.toml") == "==0.70.1"


def test_parse_environments_from_pixi_toml() -> None:
    content = """
[workspace]
name = "demo"

[environments]
dev = { features = ["dev"], no-default-feature = true }
docs = ["docs"]
"""
    assert parse_environments(content, "pixi.toml") == ["default", "dev", "docs"]


def test_parse_environments_from_pyproject() -> None:
    content = """
[project]
name = "demo"
version = "0.1.0"

[tool.pixi.environments]
dev = { features = ["dev"], no-default-feature = true }
"""
    assert parse_environments(content, "pyproject.toml") == ["default", "dev"]


def test_build_install_args() -> None:
    assert build_pixi_install_args("default") == ["pixi", "install", "--locked", "--environment", "default"]


def test_build_install_args_rejects_empty_environment() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        build_pixi_install_args("")


def test_build_install_all_args() -> None:
    assert build_pixi_install_all_args() == ["pixi", "install", "--locked", "--all"]


def test_normalize_environments() -> None:
    assert normalize_environments(["default", "docs", "default"]) == ["default", "docs"]


def test_normalize_environments_rejects_empty_list() -> None:
    with pytest.raises(ValueError, match="At least one"):
        normalize_environments([])


def test_normalize_environments_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        normalize_environments(["default", " "])


def test_normalize_runtime_source_paths() -> None:
    assert normalize_runtime_source_paths(["./pyproject.toml", "src", "src"]) == ["pyproject.toml", "src"]


def test_normalize_runtime_source_paths_defaults_to_full_source() -> None:
    assert normalize_runtime_source_paths(None) is None
    assert normalize_runtime_source_paths(["."]) is None


@pytest.mark.parametrize("path", ["", " ", "/src", "../src", "src/../secret"])
def test_normalize_runtime_source_paths_rejects_unsafe_paths(path: str) -> None:
    with pytest.raises(ValueError):
        normalize_runtime_source_paths([path])


def test_build_lock_check_args() -> None:
    assert build_pixi_lock_check_args() == ["pixi", "lock", "--check"]


def test_build_run_args() -> None:
    assert build_pixi_run_args(["python", "--version"], "dev") == [
        "pixi",
        "run",
        "--locked",
        "--environment",
        "dev",
        "python",
        "--version",
    ]


def test_build_run_args_rejects_empty_command() -> None:
    with pytest.raises(ValueError, match="requires at least one"):
        build_pixi_run_args([], "default")


def test_build_shell_hook_args() -> None:
    assert build_pixi_shell_hook_args("default") == [
        "pixi",
        "shell-hook",
        "--locked",
        "--environment",
        "default",
        "--json",
    ]


def test_build_bash_shell_hook_args() -> None:
    assert build_pixi_shell_hook_args("default", json=False, shell="bash") == [
        "pixi",
        "shell-hook",
        "--locked",
        "--environment",
        "default",
        "--shell",
        "bash",
    ]


def test_build_bash_entrypoint() -> None:
    assert build_bash_entrypoint("export PATH=/env/bin:$PATH\n") == (
        '#!/usr/bin/env bash\nset -euo pipefail\nexport PATH=/env/bin:$PATH\nexec "$@"\n'
    )

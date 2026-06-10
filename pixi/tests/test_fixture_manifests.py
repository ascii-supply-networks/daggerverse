from pathlib import Path

from pixi.utils import parse_environments, parse_requires_pixi

FIXTURES = Path(__file__).parent / "_packages"


def test_clean_fixture_manifest() -> None:
    content = (FIXTURES / "clean" / "pixi.toml").read_text(encoding="utf-8")
    assert parse_requires_pixi(content, "pixi.toml") == ">=0.70.0"
    assert parse_environments(content, "pixi.toml") == ["default"]


def test_named_env_fixture_manifest() -> None:
    content = (FIXTURES / "named-env" / "pixi.toml").read_text(encoding="utf-8")
    assert parse_environments(content, "pixi.toml") == ["default", "dev"]


def test_pyproject_fixture_manifest() -> None:
    content = (FIXTURES / "pyproject" / "pyproject.toml").read_text(encoding="utf-8")
    assert parse_requires_pixi(content, "pyproject.toml") == "==0.70.1"
    assert parse_environments(content, "pyproject.toml") == ["default", "docs"]

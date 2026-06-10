from typing import Annotated, TypeAlias

import dagger
from dagger import DefaultPath, Doc, Ignore

SourceDir = Annotated[
    dagger.Directory,
    Doc("Source directory."),
    DefaultPath("."),
    Ignore(
        [
            "**/__pycache__",
            "**/*.pyc",
            "**/.git",
            "**/.pixi",
            "**/.venv",
            "**/.pytest_cache",
            "**/.ruff_cache",
            "**/.mypy_cache",
            "**/.direnv",
            "**/.devenv",
            "**/node_modules",
            "**/dist",
            "**/build",
            "**/*.egg-info",
            "**/sdk",
        ]
    ),
]

WorkspacePath: TypeAlias = Annotated[
    str,
    Doc("Path to the workspace root holding pixi.lock within the source directory."),
]

EnvironmentName: TypeAlias = Annotated[
    str,
    Doc("Pixi environment name. Defaults to the implicit `default` environment."),
]

PixiCommand: TypeAlias = Annotated[
    list[str],
    Doc("Command argv passed to `pixi run`."),
]

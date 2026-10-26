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
            "**/.cache",
            "**/.direnv",
            "**/.devenv",
            "**/node_modules",
            "**/dist",
            "**/build",
            "**/site",
            "**/public",
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

EnvironmentNames: TypeAlias = Annotated[
    list[str],
    Doc("Pixi environment names to install into the same container."),
]

RuntimeSourcePaths: TypeAlias = Annotated[
    list[str],
    Doc("Relative source paths or glob patterns to copy into the runtime image."),
]

LockfileMode: TypeAlias = Annotated[
    str,
    Doc("Pixi lockfile mode for install, run, and shell-hook: `locked` or `frozen`. Defaults to `locked`."),
]

PixiCommand: TypeAlias = Annotated[
    list[str],
    Doc("Command argv passed to `pixi run`."),
]

AutoInstallPixi: TypeAlias = Annotated[
    bool,
    Doc(
        "Install the Pixi binary when it is not already on $PATH of `base_container`. "
        "Set to False if your base container already ships Pixi."
    ),
]

PruneCache: TypeAlias = Annotated[
    bool,
    Doc("Empty the shared Pixi cache volume after installing once it grows past `max_cache_size`."),
]

MaxCacheSize: TypeAlias = Annotated[
    int,
    Doc("Prune the Pixi cache only once it grows past this many GiB. `0` prunes on every build."),
]

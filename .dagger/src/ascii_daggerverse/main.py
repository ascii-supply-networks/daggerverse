from typing import Annotated

import dagger
from dagger import DefaultPath, Doc, Ignore, check, dag, field, function, object_type

_SOURCE_IGNORE = [
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


def _base() -> dagger.Container:
    return dag.container().from_("ghcr.io/prefix-dev/pixi:0.70.2").with_workdir("/workspace")


@object_type
class AsciiDaggerverse:
    """CI and docs helpers for the ASCII Daggerverse repository."""

    source: Annotated[
        dagger.Directory,
        Doc("Repository root."),
        DefaultPath("."),
        Ignore(_SOURCE_IGNORE),
    ] = field()

    @check
    @function
    async def python(self) -> None:
        """Run Python unit and lint checks through the root Pixi environment."""
        ctr = (
            _base()
            .with_directory("/workspace", self.source)
            .with_mounted_cache("/root/.cache/rattler/cache", dag.cache_volume("pixi-rattler-cache"))
            .with_mounted_cache("/root/.cache/pixi", dag.cache_volume("pixi-cache"))
            .with_env_variable("PIXI_NO_PROGRESS", "true")
        )
        await (
            ctr.with_exec(["pixi", "install", "--locked", "--environment", "default"])
            .with_exec(["pixi", "run", "--frozen", "test"])
            .with_exec(["pixi", "run", "--frozen", "lint"])
            .with_exec(["pixi", "run", "--frozen", "format-check"])
            .sync()
        )

    @function
    async def docs_build(self) -> dagger.Directory:
        """Build the static docs site."""
        ctr = (
            _base()
            .with_directory("/workspace", self.source)
            .with_mounted_cache("/root/.cache/rattler/cache", dag.cache_volume("pixi-rattler-cache"))
            .with_mounted_cache("/root/.cache/pixi", dag.cache_volume("pixi-cache"))
            .with_env_variable("PIXI_NO_PROGRESS", "true")
            .with_exec(["pixi", "run", "--frozen", "python", "-m", "zensical", "build", "-f", "pixi/zensical.toml"])
        )
        return ctr.directory("/workspace/pixi/site")

    @check
    @function
    async def docs(self) -> None:
        """Build the module documentation site."""
        await (await self.docs_build()).sync()

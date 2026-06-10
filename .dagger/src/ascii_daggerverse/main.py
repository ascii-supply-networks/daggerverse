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
    "**/.cache",
    "**/.direnv",
    "**/.devenv",
    "**/node_modules",
    "**/dist",
    "**/build",
    "**/site",
    "**/*.egg-info",
    "**/sdk",
]

_LANDING_PROJECT = ".docs"
_ZENSICAL_GLOB = "*/zensical.toml"


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
        """Build the combined static docs site."""
        ctr = (
            _base()
            .with_directory("/workspace", self.source)
            .with_mounted_cache("/root/.cache/rattler/cache", dag.cache_volume("pixi-rattler-cache"))
            .with_mounted_cache("/root/.cache/pixi", dag.cache_volume("pixi-cache"))
            .with_env_variable("PIXI_NO_PROGRESS", "true")
        )
        combined = await self._zensical_site(ctr, _LANDING_PROJECT)
        modules = sorted(
            module
            for module in (path.rsplit("/", 1)[0] for path in await self.source.glob(_ZENSICAL_GLOB))
            if not module.startswith(".")
        )
        for module in modules:
            combined = combined.with_directory(module, await self._zensical_site(ctr, module))
        return combined

    async def _zensical_site(self, ctr: dagger.Container, project: str) -> dagger.Directory:
        """Build one Zensical site and return its generated site directory."""
        return ctr.with_exec(
            [
                "pixi",
                "run",
                "--frozen",
                "python",
                "-m",
                "zensical",
                "build",
                "-f",
                f"{project}/zensical.toml",
                "--clean",
            ]
        ).directory(f"/workspace/{project}/site")

    @check
    @function
    async def docs(self) -> None:
        """Build the module documentation site."""
        await (await self.docs_build()).sync()

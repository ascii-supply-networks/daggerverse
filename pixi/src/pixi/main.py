from typing import Annotated

import anyio
import dagger
from dagger import Doc, check, field, function, object_type
from dagger.telemetry import get_tracer
from opentelemetry.trace import Status, StatusCode

from pixi.args import (
    EnvironmentName,
    EnvironmentNames,
    LockfileMode,
    PixiCommand,
    RuntimeSourcePaths,
    SourceDir,
    WorkspacePath,
)
from pixi.utils import is_excluded, workspace_path
from pixi.workspace.workspace import DEFAULT_RUNTIME_IMAGE, PixiWorkspaceSource


@object_type
class Pixi:
    """Entrypoint for the `pixi` module.

    Root functions operate on the workspace at `.` by default and accept `path`
    for nested Pixi workspaces. Use `workspace` when you want to keep a
    `PixiWorkspaceSource` object around explicitly.

    Learn more in the module docs and generated SDK reference.
    """

    source: SourceDir = field()

    @function
    def workspace(self, path: WorkspacePath = ".") -> PixiWorkspaceSource:
        """A single Pixi workspace at `path` within the source tree.

        The returned workspace can install environments, run commands, and build
        runtime images without the Pixi binary.
        """
        return PixiWorkspaceSource(source=self.source, path=path)

    @function
    async def environments(self, path: WorkspacePath = ".") -> list[str]:
        """Pixi environments declared by the workspace manifest."""
        return await self.workspace(path).environments()

    @function
    async def install(
        self,
        environment: EnvironmentName = "default",
        path: WorkspacePath = ".",
        base_container: Annotated[
            dagger.Container | None,
            Doc("Container to install into. Defaults to a Pixi image pinned to the workspace."),
        ] = None,
        pixi_version: Annotated[
            str | None,
            Doc("Pixi version image tag. Defaults to the version detected from the workspace."),
        ] = None,
        image: Annotated[
            str | None,
            Doc("Full Pixi image reference. Overrides `pixi_version`."),
        ] = None,
        dagger_codegen: Annotated[
            bool,
            Doc("Run Dagger codegen and overlay sdk/ when the workspace is a Dagger module."),
        ] = True,
        lockfile_mode: LockfileMode = "locked",
    ) -> dagger.Container:
        """Install one Pixi environment into a builder container."""
        return await self.workspace(path).install(
            environment=environment,
            base_container=base_container,
            pixi_version=pixi_version,
            image=image,
            dagger_codegen=dagger_codegen,
            lockfile_mode=lockfile_mode,
        )

    @function
    async def install_environments(
        self,
        environments: EnvironmentNames,
        path: WorkspacePath = ".",
        base_container: Annotated[
            dagger.Container | None,
            Doc("Container to install into. Defaults to a Pixi image pinned to the workspace."),
        ] = None,
        pixi_version: Annotated[
            str | None,
            Doc("Pixi version image tag. Defaults to the version detected from the workspace."),
        ] = None,
        image: Annotated[
            str | None,
            Doc("Full Pixi image reference. Overrides `pixi_version`."),
        ] = None,
        dagger_codegen: Annotated[
            bool,
            Doc("Run Dagger codegen and overlay sdk/ when the workspace is a Dagger module."),
        ] = True,
        lockfile_mode: LockfileMode = "locked",
    ) -> dagger.Container:
        """Install selected Pixi environments into the same builder container."""
        return await self.workspace(path).install_environments(
            environments=environments,
            base_container=base_container,
            pixi_version=pixi_version,
            image=image,
            dagger_codegen=dagger_codegen,
            lockfile_mode=lockfile_mode,
        )

    @function
    async def install_all_environments(
        self,
        path: WorkspacePath = ".",
        base_container: Annotated[
            dagger.Container | None,
            Doc("Container to install into. Defaults to a Pixi image pinned to the workspace."),
        ] = None,
        pixi_version: Annotated[
            str | None,
            Doc("Pixi version image tag. Defaults to the version detected from the workspace."),
        ] = None,
        image: Annotated[
            str | None,
            Doc("Full Pixi image reference. Overrides `pixi_version`."),
        ] = None,
        dagger_codegen: Annotated[
            bool,
            Doc("Run Dagger codegen and overlay sdk/ when the workspace is a Dagger module."),
        ] = True,
        lockfile_mode: LockfileMode = "locked",
    ) -> dagger.Container:
        """Install every Pixi environment into the same builder container."""
        return await self.workspace(path).install_all_environments(
            base_container=base_container,
            pixi_version=pixi_version,
            image=image,
            dagger_codegen=dagger_codegen,
            lockfile_mode=lockfile_mode,
        )

    @function
    async def runtime(
        self,
        environment: EnvironmentName = "default",
        path: WorkspacePath = ".",
        runtime_base_container: Annotated[
            dagger.Container | None,
            Doc("Runtime base container. Defaults to `ubuntu:noble`."),
        ] = None,
        runtime_image: Annotated[
            str,
            Doc("Runtime image used when `runtime_base_container` is not set."),
        ] = DEFAULT_RUNTIME_IMAGE,
        base_container: Annotated[
            dagger.Container | None,
            Doc("Builder container to install with Pixi. Defaults to a Pixi image pinned to the workspace."),
        ] = None,
        pixi_version: Annotated[
            str | None,
            Doc("Pixi version image tag for the builder. Defaults to the version detected from the workspace."),
        ] = None,
        image: Annotated[
            str | None,
            Doc("Full Pixi builder image reference. Overrides `pixi_version`."),
        ] = None,
        runtime_source_paths: Annotated[
            RuntimeSourcePaths | None,
            Doc("Relative source paths or glob patterns to copy into the runtime image. Defaults to the full source."),
        ] = None,
        dagger_codegen: Annotated[
            bool,
            Doc("Run Dagger codegen and overlay sdk/ when the workspace is a Dagger module."),
        ] = True,
        lockfile_mode: LockfileMode = "locked",
    ) -> dagger.Container:
        """Build a runtime container with one Pixi environment and no Pixi binary."""
        return await self.workspace(path).runtime(
            environment=environment,
            runtime_base_container=runtime_base_container,
            runtime_image=runtime_image,
            base_container=base_container,
            pixi_version=pixi_version,
            image=image,
            runtime_source_paths=runtime_source_paths,
            dagger_codegen=dagger_codegen,
            lockfile_mode=lockfile_mode,
        )

    @function
    async def runtime_environments(
        self,
        environments: EnvironmentNames,
        entrypoint_environment: EnvironmentName = "default",
        path: WorkspacePath = ".",
        runtime_base_container: Annotated[
            dagger.Container | None,
            Doc("Runtime base container. Defaults to `ubuntu:noble`."),
        ] = None,
        runtime_image: Annotated[
            str,
            Doc("Runtime image used when `runtime_base_container` is not set."),
        ] = DEFAULT_RUNTIME_IMAGE,
        base_container: Annotated[
            dagger.Container | None,
            Doc("Builder container to install with Pixi. Defaults to a Pixi image pinned to the workspace."),
        ] = None,
        pixi_version: Annotated[
            str | None,
            Doc("Pixi version image tag for the builder. Defaults to the version detected from the workspace."),
        ] = None,
        image: Annotated[
            str | None,
            Doc("Full Pixi builder image reference. Overrides `pixi_version`."),
        ] = None,
        runtime_source_paths: Annotated[
            RuntimeSourcePaths | None,
            Doc("Relative source paths or glob patterns to copy into the runtime image. Defaults to the full source."),
        ] = None,
        dagger_codegen: Annotated[
            bool,
            Doc("Run Dagger codegen and overlay sdk/ when the workspace is a Dagger module."),
        ] = True,
        lockfile_mode: LockfileMode = "locked",
    ) -> dagger.Container:
        """Build a runtime container with selected Pixi environments and no Pixi binary."""
        return await self.workspace(path).runtime_environments(
            environments=environments,
            entrypoint_environment=entrypoint_environment,
            runtime_base_container=runtime_base_container,
            runtime_image=runtime_image,
            base_container=base_container,
            pixi_version=pixi_version,
            image=image,
            runtime_source_paths=runtime_source_paths,
            dagger_codegen=dagger_codegen,
            lockfile_mode=lockfile_mode,
        )

    @function
    async def runtime_all_environments(
        self,
        entrypoint_environment: EnvironmentName = "default",
        path: WorkspacePath = ".",
        runtime_base_container: Annotated[
            dagger.Container | None,
            Doc("Runtime base container. Defaults to `ubuntu:noble`."),
        ] = None,
        runtime_image: Annotated[
            str,
            Doc("Runtime image used when `runtime_base_container` is not set."),
        ] = DEFAULT_RUNTIME_IMAGE,
        base_container: Annotated[
            dagger.Container | None,
            Doc("Builder container to install with Pixi. Defaults to a Pixi image pinned to the workspace."),
        ] = None,
        pixi_version: Annotated[
            str | None,
            Doc("Pixi version image tag for the builder. Defaults to the version detected from the workspace."),
        ] = None,
        image: Annotated[
            str | None,
            Doc("Full Pixi builder image reference. Overrides `pixi_version`."),
        ] = None,
        runtime_source_paths: Annotated[
            RuntimeSourcePaths | None,
            Doc("Relative source paths or glob patterns to copy into the runtime image. Defaults to the full source."),
        ] = None,
        dagger_codegen: Annotated[
            bool,
            Doc("Run Dagger codegen and overlay sdk/ when the workspace is a Dagger module."),
        ] = True,
        lockfile_mode: LockfileMode = "locked",
    ) -> dagger.Container:
        """Build a runtime container with every Pixi environment and no Pixi binary."""
        return await self.workspace(path).runtime_all_environments(
            entrypoint_environment=entrypoint_environment,
            runtime_base_container=runtime_base_container,
            runtime_image=runtime_image,
            base_container=base_container,
            pixi_version=pixi_version,
            image=image,
            runtime_source_paths=runtime_source_paths,
            dagger_codegen=dagger_codegen,
            lockfile_mode=lockfile_mode,
        )

    @function
    async def run(
        self,
        args: PixiCommand,
        environment: EnvironmentName = "default",
        path: WorkspacePath = ".",
        base_container: Annotated[
            dagger.Container | None,
            Doc("Container to run in. Defaults to a Pixi image pinned to the workspace."),
        ] = None,
        pixi_version: Annotated[
            str | None,
            Doc("Pixi version image tag. Defaults to the version detected from the workspace."),
        ] = None,
        image: Annotated[
            str | None,
            Doc("Full Pixi image reference. Overrides `pixi_version`."),
        ] = None,
        dagger_codegen: Annotated[
            bool,
            Doc("Run Dagger codegen and overlay sdk/ when the workspace is a Dagger module."),
        ] = True,
        lockfile_mode: LockfileMode = "locked",
    ) -> dagger.Container:
        """Install one environment and run a command through Pixi."""
        return await self.workspace(path).run(
            args=args,
            environment=environment,
            base_container=base_container,
            pixi_version=pixi_version,
            image=image,
            dagger_codegen=dagger_codegen,
            lockfile_mode=lockfile_mode,
        )

    @function
    async def get_workspaces(self) -> list[PixiWorkspaceSource]:
        """Every Pixi workspace in the source tree, one per pixi.lock."""
        lockfiles = sorted(await self.source.glob("**/pixi.lock"))
        return [PixiWorkspaceSource(source=self.source, path=workspace_path(lockfile)) for lockfile in lockfiles]

    @check
    @function
    async def locked(
        self,
        exclude: Annotated[
            list[str] | None,
            Doc("Glob patterns of workspace paths to skip, e.g. `**/tests/_packages/**`."),
        ] = None,
        pixi_version: Annotated[
            str | None,
            Doc("Pixi version image tag. Defaults to the version detected per workspace."),
        ] = None,
        image: Annotated[
            str | None,
            Doc("Full Pixi image reference. Overrides `pixi_version`."),
        ] = None,
    ) -> None:
        """Verify every Pixi workspace lock file is up to date."""
        patterns = exclude or []
        workspaces = [ws for ws in await self.get_workspaces() if not is_excluded(ws.path, patterns)]
        tracer = get_tracer()
        failed: list[str] = []

        async def _run(ws: PixiWorkspaceSource) -> None:
            with tracer.start_as_current_span(f"locked({ws.path})") as span:
                try:
                    await ws.locked(pixi_version=pixi_version, image=image)
                except dagger.ExecError as exc:
                    message = "\n".join(part for part in (exc.stdout, exc.stderr) if part).strip()
                    span.set_status(Status(StatusCode.ERROR, message or f"pixi locked failed for {ws.path}"))
                    span.record_exception(exc)
                    failed.append(ws.path)
                except Exception as exc:
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    span.record_exception(exc)
                    failed.append(ws.path)

        async with anyio.create_task_group() as tg:
            for ws in workspaces:
                tg.start_soon(_run, ws)

        if failed:
            msg = f"pixi locked failed for {len(failed)} of {len(workspaces)} workspace(s): {', '.join(sorted(failed))}"
            raise RuntimeError(msg)

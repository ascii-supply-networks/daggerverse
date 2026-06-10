import posixpath
from typing import Annotated

import dagger
from dagger import Doc, dag, field, function, object_type
from dagger.telemetry import get_tracer

from pixi.args import EnvironmentName, EnvironmentNames, PixiCommand
from pixi.utils import (
    _DEFAULT_VERSION,
    build_bash_entrypoint,
    build_pixi_install_all_args,
    build_pixi_install_args,
    build_pixi_lock_check_args,
    build_pixi_run_args,
    build_pixi_shell_hook_args,
    image_ref,
    normalize_environments,
    parse_environments,
    parse_requires_pixi,
    resolve_specifier,
)
from pixi.workspace._codegen import dagger_codegen as _run_codegen

_DEFAULT_RUNTIME_IMAGE = "ubuntu:noble"
_RUNTIME_ENTRYPOINT = "/usr/local/bin/pixi-entrypoint"


@object_type
class PixiWorkspaceSource:
    """A Pixi workspace rooted at a pixi.lock."""

    source: Annotated[
        dagger.Directory,
        Doc("Source tree containing the workspace and any sibling path dependencies."),
    ] = field()

    path: Annotated[
        str,
        Doc("Workspace root path holding pixi.lock. `.` for a root workspace."),
    ] = field(default=".")

    def _ws_dir(self) -> dagger.Directory:
        return self.source if self.path == "." else self.source.directory(self.path)

    async def _manifest_name(self) -> str:
        entries = set(await self._ws_dir().entries())
        if "pixi.toml" in entries:
            return "pixi.toml"
        if "pyproject.toml" in entries:
            return "pyproject.toml"
        msg = f"No Pixi manifest found in workspace {self.path!r}; expected pixi.toml or pyproject.toml."
        raise ValueError(msg)

    async def _manifest_contents(self) -> tuple[str, str]:
        name = await self._manifest_name()
        return name, await self._ws_dir().file(name).contents()

    async def _resolved_image(self, pixi_version: str | None, image: str | None) -> str:
        if image is not None:
            return image
        return image_ref(pixi_version or await self.pixi_version())

    async def _source_with_codegen(self, dagger_codegen: bool) -> dagger.Directory:
        if not dagger_codegen:
            return self.source
        ws_dir = await _run_codegen(self._ws_dir(), ".")
        if self.path == ".":
            return ws_dir
        return self.source.with_directory(self.path, ws_dir)

    async def _install_base(
        self,
        *,
        base_container: dagger.Container | None,
        pixi_version: str | None,
        image: str | None,
        dagger_codegen: bool,
    ) -> dagger.Container:
        source = await self._source_with_codegen(dagger_codegen)
        image_ref_value = await self._resolved_image(pixi_version, image)
        ctr = base_container if base_container is not None else dag.container().from_(image_ref_value)
        workdir = "/work" if self.path == "." else posixpath.join("/work", self.path)
        return (
            ctr.with_mounted_cache("/root/.cache/rattler/cache", dag.cache_volume("pixi-rattler-cache"))
            .with_mounted_cache("/root/.cache/pixi", dag.cache_volume("pixi-cache"))
            .with_directory("/work", source)
            .with_workdir(workdir)
            .with_env_variable("PIXI_NO_PROGRESS", "true")
        )

    def _workdir(self) -> str:
        return "/work" if self.path == "." else posixpath.join("/work", self.path)

    def _env_dir(self, environment: str) -> str:
        return posixpath.join(self._workdir(), ".pixi", "envs", environment)

    @function
    async def pixi_version(self) -> str:
        """The Pixi version this workspace requires as a concrete image tag."""
        name, content = await self._manifest_contents()
        specifier = parse_requires_pixi(content, name)
        if specifier is None:
            return _DEFAULT_VERSION
        return resolve_specifier(specifier)

    @function
    async def environments(self) -> list[str]:
        """Pixi environments declared by the workspace manifest."""
        name, content = await self._manifest_contents()
        return parse_environments(content, name)

    @function
    async def install(
        self,
        environment: EnvironmentName = "default",
        base_container: Annotated[
            dagger.Container | None,
            Doc("Container to install into. Defaults to a Pixi image pinned to this workspace."),
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
    ) -> dagger.Container:
        """Install a Pixi environment from the committed lock file."""
        return await self.install_environments(
            environments=[environment],
            base_container=base_container,
            pixi_version=pixi_version,
            image=image,
            dagger_codegen=dagger_codegen,
        )

    @function
    async def install_environments(
        self,
        environments: EnvironmentNames,
        base_container: Annotated[
            dagger.Container | None,
            Doc("Container to install into. Defaults to a Pixi image pinned to this workspace."),
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
    ) -> dagger.Container:
        """Install selected Pixi environments into one container."""
        names = normalize_environments(environments)
        with get_tracer().start_as_current_span("pixi install") as span:
            span.set_attribute("workspace.path", self.path)
            span.set_attribute("pixi.environments", ",".join(names))
            ctr = await self._install_base(
                base_container=base_container,
                pixi_version=pixi_version,
                image=image,
                dagger_codegen=dagger_codegen,
            )
            for environment in names:
                args = build_pixi_install_args(environment)
                span.add_event(
                    "pixi install environment", {"pixi.environment": environment, "pixi.install_args": " ".join(args)}
                )
                ctr = ctr.with_exec(args)
            return await ctr.sync()

    @function
    async def install_all_environments(
        self,
        base_container: Annotated[
            dagger.Container | None,
            Doc("Container to install into. Defaults to a Pixi image pinned to this workspace."),
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
    ) -> dagger.Container:
        """Install every Pixi environment declared by the lock file into one container."""
        with get_tracer().start_as_current_span("pixi install all") as span:
            span.set_attribute("workspace.path", self.path)
            args = build_pixi_install_all_args()
            span.set_attribute("pixi.install_args", " ".join(args))
            ctr = await self._install_base(
                base_container=base_container,
                pixi_version=pixi_version,
                image=image,
                dagger_codegen=dagger_codegen,
            )
            return await ctr.with_exec(args).sync()

    @function
    async def runtime(
        self,
        environment: EnvironmentName = "default",
        runtime_base_container: Annotated[
            dagger.Container | None,
            Doc("Runtime base container. Defaults to `ubuntu:noble`."),
        ] = None,
        runtime_image: Annotated[
            str,
            Doc("Runtime image used when `runtime_base_container` is not set."),
        ] = _DEFAULT_RUNTIME_IMAGE,
        base_container: Annotated[
            dagger.Container | None,
            Doc("Builder container to install with Pixi. Defaults to a Pixi image pinned to this workspace."),
        ] = None,
        pixi_version: Annotated[
            str | None,
            Doc("Pixi version image tag for the builder. Defaults to the version detected from the workspace."),
        ] = None,
        image: Annotated[
            str | None,
            Doc("Full Pixi builder image reference. Overrides `pixi_version`."),
        ] = None,
        dagger_codegen: Annotated[
            bool,
            Doc("Run Dagger codegen and overlay sdk/ when the workspace is a Dagger module."),
        ] = True,
    ) -> dagger.Container:
        """Build a runtime container with one Pixi environment and no Pixi binary."""
        return await self.runtime_environments(
            environments=[environment],
            entrypoint_environment=environment,
            runtime_base_container=runtime_base_container,
            runtime_image=runtime_image,
            base_container=base_container,
            pixi_version=pixi_version,
            image=image,
            dagger_codegen=dagger_codegen,
        )

    @function
    async def runtime_environments(
        self,
        environments: EnvironmentNames,
        entrypoint_environment: EnvironmentName = "default",
        runtime_base_container: Annotated[
            dagger.Container | None,
            Doc("Runtime base container. Defaults to `ubuntu:noble`."),
        ] = None,
        runtime_image: Annotated[
            str,
            Doc("Runtime image used when `runtime_base_container` is not set."),
        ] = _DEFAULT_RUNTIME_IMAGE,
        base_container: Annotated[
            dagger.Container | None,
            Doc("Builder container to install with Pixi. Defaults to a Pixi image pinned to this workspace."),
        ] = None,
        pixi_version: Annotated[
            str | None,
            Doc("Pixi version image tag for the builder. Defaults to the version detected from the workspace."),
        ] = None,
        image: Annotated[
            str | None,
            Doc("Full Pixi builder image reference. Overrides `pixi_version`."),
        ] = None,
        dagger_codegen: Annotated[
            bool,
            Doc("Run Dagger codegen and overlay sdk/ when the workspace is a Dagger module."),
        ] = True,
    ) -> dagger.Container:
        """Build a runtime container with selected Pixi environments and no Pixi binary."""
        names = normalize_environments([entrypoint_environment, *environments])
        builder = await self.install_environments(
            environments=names,
            base_container=base_container,
            pixi_version=pixi_version,
            image=image,
            dagger_codegen=dagger_codegen,
        )
        return await self._runtime_from_builder(
            builder=builder,
            environments=names,
            entrypoint_environment=entrypoint_environment,
            runtime_base_container=runtime_base_container,
            runtime_image=runtime_image,
            dagger_codegen=dagger_codegen,
        )

    @function
    async def runtime_all_environments(
        self,
        entrypoint_environment: EnvironmentName = "default",
        runtime_base_container: Annotated[
            dagger.Container | None,
            Doc("Runtime base container. Defaults to `ubuntu:noble`."),
        ] = None,
        runtime_image: Annotated[
            str,
            Doc("Runtime image used when `runtime_base_container` is not set."),
        ] = _DEFAULT_RUNTIME_IMAGE,
        base_container: Annotated[
            dagger.Container | None,
            Doc("Builder container to install with Pixi. Defaults to a Pixi image pinned to this workspace."),
        ] = None,
        pixi_version: Annotated[
            str | None,
            Doc("Pixi version image tag for the builder. Defaults to the version detected from the workspace."),
        ] = None,
        image: Annotated[
            str | None,
            Doc("Full Pixi builder image reference. Overrides `pixi_version`."),
        ] = None,
        dagger_codegen: Annotated[
            bool,
            Doc("Run Dagger codegen and overlay sdk/ when the workspace is a Dagger module."),
        ] = True,
    ) -> dagger.Container:
        """Build a runtime container with every Pixi environment and no Pixi binary."""
        names = normalize_environments(await self.environments())
        if entrypoint_environment not in names:
            msg = f"Entrypoint environment {entrypoint_environment!r} is not declared by workspace {self.path!r}."
            raise ValueError(msg)
        builder = await self.install_all_environments(
            base_container=base_container,
            pixi_version=pixi_version,
            image=image,
            dagger_codegen=dagger_codegen,
        )
        return await self._runtime_from_builder(
            builder=builder,
            environments=names,
            entrypoint_environment=entrypoint_environment,
            runtime_base_container=runtime_base_container,
            runtime_image=runtime_image,
            dagger_codegen=dagger_codegen,
        )

    async def _runtime_from_builder(
        self,
        *,
        builder: dagger.Container,
        environments: list[str],
        entrypoint_environment: str,
        runtime_base_container: dagger.Container | None,
        runtime_image: str,
        dagger_codegen: bool,
    ) -> dagger.Container:
        source = await self._source_with_codegen(dagger_codegen)
        workdir = self._workdir()
        shell_hook = await builder.with_exec(
            build_pixi_shell_hook_args(entrypoint_environment, json=False, shell="bash")
        ).stdout()
        runtime = runtime_base_container if runtime_base_container is not None else dag.container().from_(runtime_image)
        runtime = (
            runtime.with_directory("/work", source)
            .with_workdir(workdir)
            .with_new_file(_RUNTIME_ENTRYPOINT, build_bash_entrypoint(shell_hook), permissions=0o755)
            .with_entrypoint([_RUNTIME_ENTRYPOINT])
        )
        for environment in environments:
            runtime = runtime.with_directory(self._env_dir(environment), builder.directory(self._env_dir(environment)))
        return await runtime.sync()

    @function
    async def locked(
        self,
        pixi_version: Annotated[
            str | None,
            Doc("Pixi version image tag. Defaults to the version detected from the workspace."),
        ] = None,
        image: Annotated[
            str | None,
            Doc("Full Pixi image reference. Overrides `pixi_version`."),
        ] = None,
    ) -> None:
        """Verify this workspace's lock file is up to date for all environments."""
        with get_tracer().start_as_current_span("pixi locked") as span:
            span.set_attribute("workspace.path", self.path)
            source = self.source
            image_ref_value = await self._resolved_image(pixi_version, image)
            workdir = "/work" if self.path == "." else posixpath.join("/work", self.path)
            args = build_pixi_lock_check_args()
            span.set_attribute("pixi.lock_args", args)
            await (
                dag.container()
                .from_(image_ref_value)
                .with_mounted_cache("/root/.cache/rattler/cache", dag.cache_volume("pixi-rattler-cache"))
                .with_mounted_cache("/root/.cache/pixi", dag.cache_volume("pixi-cache"))
                .with_directory("/work", source)
                .with_workdir(workdir)
                .with_env_variable("PIXI_NO_PROGRESS", "true")
                .with_exec(args)
                .sync()
            )

    @function
    async def run(
        self,
        args: PixiCommand,
        environment: EnvironmentName = "default",
        base_container: Annotated[
            dagger.Container | None,
            Doc("Container to run in. Defaults to a Pixi image pinned to this workspace."),
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
    ) -> dagger.Container:
        """Install the environment and run a command through `pixi run`."""
        ctr = await self.install(
            environment=environment,
            base_container=base_container,
            pixi_version=pixi_version,
            image=image,
            dagger_codegen=dagger_codegen,
        )
        command = build_pixi_run_args(args, environment)
        with get_tracer().start_as_current_span("pixi run") as span:
            span.set_attribute("pixi.run_args", command)
            return await ctr.with_exec(command).sync()

    @function
    async def shell_hook(
        self,
        environment: EnvironmentName = "default",
        json: Annotated[bool, Doc("Emit shell hook environment as JSON.")] = True,
        pixi_version: Annotated[
            str | None,
            Doc("Pixi version image tag. Defaults to the version detected from the workspace."),
        ] = None,
        image: Annotated[
            str | None,
            Doc("Full Pixi image reference. Overrides `pixi_version`."),
        ] = None,
    ) -> str:
        """Return Pixi's activation shell hook for a named environment."""
        image_ref_value = await self._resolved_image(pixi_version, image)
        workdir = "/work" if self.path == "." else posixpath.join("/work", self.path)
        args = build_pixi_shell_hook_args(environment, json=json)
        return await (
            dag.container()
            .from_(image_ref_value)
            .with_directory("/work", self.source)
            .with_workdir(workdir)
            .with_env_variable("PIXI_NO_PROGRESS", "true")
            .with_exec(args)
            .stdout()
        )

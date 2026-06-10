from typing import Annotated

import anyio
import dagger
from dagger import Doc, check, field, function, object_type
from dagger.telemetry import get_tracer
from opentelemetry.trace import Status, StatusCode

from pixi.args import SourceDir, WorkspacePath
from pixi.utils import is_excluded, workspace_path
from pixi.workspace.workspace import PixiWorkspaceSource


@object_type
class Pixi:
    """Entrypoint for the `pixi` module."""

    source: SourceDir = field()

    @function
    def workspace(self, path: WorkspacePath = ".") -> PixiWorkspaceSource:
        """A single Pixi workspace at `path` within the source tree."""
        return PixiWorkspaceSource(source=self.source, path=path)

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

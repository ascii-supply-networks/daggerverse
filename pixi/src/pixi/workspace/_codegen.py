import posixpath

import dagger
from dagger import dag
from dagger.telemetry import get_tracer

from pixi.utils import needs_dagger_codegen


async def _manifest(ws_dir: dagger.Directory, codegen_path: str) -> tuple[str, str] | None:
    for name in ("pixi.toml", "pyproject.toml"):
        path = name if codegen_path == "." else posixpath.join(codegen_path, name)
        if await ws_dir.glob(path):
            return name, await ws_dir.file(path).contents()
    return None


async def dagger_codegen(ws_dir: dagger.Directory, codegen_path: str) -> dagger.Directory:
    """Run Dagger codegen and overlay the generated SDK.

    No-op unless *both* ``dagger.json`` and a Pixi manifest with ``dagger-io``
    sourced from a local ``sdk`` directory exist at *codegen_path*.
    """
    tracer = get_tracer()

    with tracer.start_as_current_span("detect dagger module") as span:
        span.set_attribute("codegen.path", codegen_path)
        dagger_json_path = "dagger.json" if codegen_path == "." else posixpath.join(codegen_path, "dagger.json")
        if not await ws_dir.glob(dagger_json_path):
            span.set_attribute("codegen.skipped", True)
            span.set_attribute("codegen.skip_reason", "no dagger.json")
            return ws_dir
        manifest = await _manifest(ws_dir, codegen_path)
        if manifest is None or not needs_dagger_codegen(manifest[1], manifest[0]):
            span.set_attribute("codegen.skipped", True)
            span.set_attribute("codegen.skip_reason", "no local dagger-io source")
            return ws_dir
        dagger_json_contents = await ws_dir.file(dagger_json_path).contents()

    with tracer.start_as_current_span("run dagger codegen") as span:
        span.set_attribute("codegen.path", codegen_path)
        generated = (
            dag.directory()
            .with_new_file("dagger.json", dagger_json_contents)
            .as_module_source()
            .generated_context_directory()
        )
        sdk_overlay_path = "sdk" if codegen_path == "." else posixpath.join(codegen_path, "sdk")
        result = ws_dir.with_directory(sdk_overlay_path, generated.directory("sdk"))
        return await result.sync()

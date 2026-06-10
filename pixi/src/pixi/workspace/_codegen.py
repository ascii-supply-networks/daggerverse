import posixpath

import dagger
from dagger import dag
from dagger.telemetry import get_tracer


async def dagger_codegen(ws_dir: dagger.Directory, codegen_path: str) -> dagger.Directory:
    """Run Dagger codegen and overlay the generated SDK. No-op without dagger.json."""
    with get_tracer().start_as_current_span("dagger codegen") as span:
        span.set_attribute("codegen.path", codegen_path)
        dagger_json_path = "dagger.json" if codegen_path == "." else posixpath.join(codegen_path, "dagger.json")
        if not await ws_dir.glob(dagger_json_path):
            return ws_dir
        dagger_json_contents = await ws_dir.file(dagger_json_path).contents()
        generated = (
            dag.directory()
            .with_new_file("dagger.json", dagger_json_contents)
            .as_module_source()
            .generated_context_directory()
        )
        sdk_overlay_path = "sdk" if codegen_path == "." else posixpath.join(codegen_path, "sdk")
        result = ws_dir.with_directory(sdk_overlay_path, generated.directory("sdk"))
        return await result.sync()

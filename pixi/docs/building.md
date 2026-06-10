---
icon: lucide/terminal
title: Building containers
description: Install and run Pixi environments inside Dagger containers.
---

# Building Containers

`install` copies the source tree into a Pixi image, mounts Pixi caches, and runs
`pixi install --locked` for a named environment inside a
[Dagger](https://dagger.io) container. The returned container is a builder-style
container and includes the Pixi binary.

```python
from dagger import dag

ctr = await dag.pixi(source=src).install(environment="default")
```

Install more than one environment into the same container:

```python
ctr = await dag.pixi(source=src).install_environments(environments=["default", "docs"])
```

Use `run` for one-off commands:

```python
ctr = await dag.pixi(source=src).run(args=["python", "--version"])
```

Use `runtime` for a deployable image without Pixi. It installs with Pixi in a
builder, copies the selected `.pixi/envs/*` directories and a Bash entrypoint
into a runtime image, and leaves the Pixi binary behind.

```python
runtime = await dag.pixi(source=src).runtime(environment="default")
```

For a final image with several Pixi environments:

```python
runtime = await dag.pixi(source=src).runtime_environments(
    environments=["default", "model-downloader"],
    entrypoint_environment="default",
)
```

For a tighter runtime image, copy only the source paths that target needs:

```python
runtime = await dag.pixi(source=src).runtime_environments(
    environments=["default", "model-downloader"],
    entrypoint_environment="default",
    runtime_source_paths=[
        "pyproject.toml",
        "pixi.lock",
        "src/shared_library",
        "src/codelocation_patents_v2/codelocation_patents_v2",
        "src/codelocation_patents_v2/scripts",
        "src/codelocation_patents_v2/config",
    ],
)
```

Use `path` when the Pixi workspace is not at the source root:

```python
ctr = await dag.pixi(source=src).install_environments(
    path="services/api",
    environments=["default", "docs"],
)
```

Pixi features become concrete through environments. For example, an environment
declared with `features = ["docs"]` is installed by passing the environment name,
not the feature name.

The default runtime image is `ubuntu:noble`. Pass `runtime_image` or
`runtime_base_container` to add operating-system packages before the Pixi
environments are copied in.

The default image is `ghcr.io/prefix-dev/pixi:0.70.2`. Pass `image` or
`pixi_version` to override the builder image.

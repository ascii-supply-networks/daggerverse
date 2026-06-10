---
icon: lucide/terminal
title: Building containers
description: Install and run Pixi environments inside Dagger containers.
---

# Building Containers

`install` copies the source tree into a Pixi image, mounts Pixi caches, and runs
`pixi install --locked` for the selected environment inside a
[Dagger](https://dagger.io) container. The returned container is a builder-style
container and includes the Pixi binary.

```python
from dagger import dag

ctr = await dag.pixi(source=src).workspace().install(environment="default")
```

Install more than one environment into the same container:

```python
ctr = await dag.pixi(source=src).workspace().install_environments(environments=["default", "docs"])
```

Use `run` for one-off commands:

```python
ctr = await dag.pixi(source=src).workspace().run(args=["python", "--version"])
```

Use `runtime` for a deployable image without Pixi. It installs with Pixi in a
builder, copies the selected `.pixi/envs/*` directories and a Bash entrypoint
into a runtime image, and leaves the Pixi binary behind.

```python
runtime = await dag.pixi(source=src).workspace().runtime(environment="default")
```

For a final image with several Pixi environments:

```python
runtime = await dag.pixi(source=src).workspace().runtime_environments(
    environments=["default", "model-downloader"],
    entrypoint_environment="default",
)
```

The default runtime image is `ubuntu:noble`. Pass `runtime_image` or
`runtime_base_container` to add operating-system packages before the Pixi
environments are copied in.

The default image is `ghcr.io/prefix-dev/pixi:0.70.2`. Pass `image` or
`pixi_version` to override the builder image.

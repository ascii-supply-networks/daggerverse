---
icon: lucide/terminal
title: Building containers
description: Install and run Pixi environments inside Dagger containers.
---

# Building Containers

`install` copies the source tree into a Pixi image, mounts Pixi caches, and runs
`pixi install --locked` for the selected environment inside a
[Dagger](https://dagger.io) container.

```python
from dagger import dag

ctr = await dag.pixi(source=src).workspace().install(environment="default")
```

Use `run` for one-off commands:

```python
ctr = await dag.pixi(source=src).workspace().run(args=["python", "--version"])
```

The default image is `ghcr.io/prefix-dev/pixi:0.70.2`. Pass `image` or
`pixi_version` to override it.

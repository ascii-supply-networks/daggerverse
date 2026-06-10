---
icon: lucide/package
title: Overview
description: A Dagger module for Pixi-managed Python projects and environments.
---

# pixi

A [Dagger](https://dagger.io) module for [Pixi](https://pixi.prefix.dev/latest/)
Python projects.

!!! note "API reference"

    This site is a tutorial. The generated SDK reference is published on the
    [Daggerverse](https://daggerverse.dev/mod/github.com/ascii-supply-networks/daggerverse/pixi).

!!! note "Upstream inspiration"

    This module is heavily inspired by the
    [`uv` module](https://daggerverse.docs.typesafe.ai/uv/) in
    [`typesafe-ai/daggerverse`](https://github.com/typesafe-ai/daggerverse), adapted
    from uv-managed Python workspaces to Pixi-managed workspaces.

The module keeps Pixi itself as the authority for dependency installation. It
installs named Pixi environments in [Dagger](https://dagger.io) containers,
runs commands through Pixi, and builds runtime images without the Pixi binary.

## Installation

```console
$ dagger install github.com/ascii-supply-networks/daggerverse/pixi
```

## Quickstart

=== "CLI"

    ```console
    $ dagger call pixi install --environment default
    $ dagger call pixi install-environments --environments default --environments docs
    $ dagger call pixi runtime-environments --environments default --environments docs
    $ dagger call pixi run --args python --args --version
    ```

=== "Python SDK"

    ```python
    from dagger import dag

    ctr = await dag.pixi(source=src).install(environment="default")
    runtime = await dag.pixi(source=src).runtime_environments(
        environments=["default", "docs"],
        entrypoint_environment="default",
    )
    ```

Pass `--path` only when the source tree contains more than one Pixi workspace.

## API Shape

- `Pixi` holds the source tree and exposes the default workspace at `.`.
- `PixiWorkspaceSource` represents a nested workspace rooted at a `pixi.lock`.
- `install` creates a Pixi-based container with one named environment installed.
- `install_environments` installs selected environments into the same Pixi-based container.
- `runtime` and `runtime_environments` copy installed Pixi environments into a runtime image without the Pixi binary.
- `runtime_source_paths` limits runtime images to the source paths a target needs.
- `run` executes a command through Pixi in a named environment.

Pixi features are not installed directly. Define environments from features in
`pyproject.toml` or `pixi.toml`, then pass those environment names to the module.

## Where to go next

- [Building containers](building.md) - install and run Pixi environments in Dagger containers.
- [Environments and features](environments.md) - map Pixi features to installable environments.
- [SDK reference](https://daggerverse.dev/mod/github.com/ascii-supply-networks/daggerverse/pixi)

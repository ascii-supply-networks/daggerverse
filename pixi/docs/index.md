---
icon: lucide/package
title: Overview
description: A Dagger module for Pixi-managed workspaces.
---

# pixi

A [Dagger](https://dagger.io) module for [Pixi](https://pixi.prefix.dev/latest/)
workspaces.

!!! note "API reference"

    This site is a tutorial. The generated SDK reference is published on the
    [Daggerverse](https://daggerverse.dev/mod/github.com/ascii-supply-networks/daggerverse/pixi).

!!! note "Upstream inspiration"

    This module is heavily inspired by the
    [`uv` module](https://daggerverse.docs.typesafe.ai/uv/) in
    [`typesafe-ai/daggerverse`](https://github.com/typesafe-ai/daggerverse), adapted
    from uv-managed Python workspaces to Pixi-managed workspaces.

The module keeps Pixi itself as the authority for dependency installation and lock
validation. It discovers workspaces by `pixi.lock`, reads manifests for stable
metadata, and runs `pixi install` / `pixi run` in containers.

## Installation

```console
dagger install github.com/ascii-supply-networks/daggerverse/pixi
```

## Quickstart

```console
dagger call pixi workspace install --environment default
dagger call pixi workspace install-environments --environments default --environments docs
dagger call pixi workspace runtime --environment default
dagger call pixi workspace run --args python --args --version
dagger check pixi:locked
```

## API Shape

- `Pixi` holds the source tree and discovers workspaces.
- `PixiWorkspaceSource` represents one workspace rooted at a `pixi.lock`.
- `locked` checks that committed locks are up to date.
- `install` creates a Pixi-based container with one named environment installed.
- `install_environments` installs selected environments into the same Pixi-based container.
- `runtime` and `runtime_environments` copy installed Pixi environments into a runtime image without the Pixi binary.
- `run` executes a command through Pixi in a named environment.

## Where to go next

- [Building containers](building.md) - install and run Pixi environments in Dagger containers.
- [GitHub Actions](github-actions.md) - run CI, publish to Daggerverse, and deploy docs.
- [Lock checks](checks/locked.md) - verify committed Pixi locks.

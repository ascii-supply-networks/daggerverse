---
icon: lucide/box
title: Environments and features
description: Use Pixi features to define environments, then install those environments in Dagger containers.
---

# Environments and features

Pixi features are reusable chunks of project configuration. They can add
dependencies, PyPI dependencies, tasks, channels, platforms, activation scripts,
and system requirements. Pixi environments are the named, installable combinations
of those features.

This module works at the environment level because that is what Pixi installs and
runs. Define features in `pyproject.toml` or `pixi.toml`, compose them into
environments, then pass those environment names to Dagger.

## Define environments

```toml
[tool.pixi.dependencies]
python = ">=3.13,<3.15"

[tool.pixi.feature.docs.dependencies]
mkdocs = ">=1.6,<2"

[tool.pixi.feature.model.dependencies]
pytorch = ">=2.5,<3"

[tool.pixi.environments]
default = { solve-group = "default" }
docs = { features = ["docs"], no-default-feature = true }
model = { features = ["model"] }
```

In this example:

- `default` installs the base dependencies.
- `docs` installs only the `docs` feature because `no-default-feature = true`.
- `model` installs base dependencies plus the `model` feature.

## List environments

=== "CLI"

    ```console
    $ dagger call pixi environments
    ```

=== "Python SDK"

    ```python
    names = await dag.pixi(source=src).environments()
    ```

For a nested workspace, pass `path`:

```console
$ dagger call pixi environments --path services/api
```

## Install several environments

Several environments can live in the same returned container:

=== "CLI"

    ```console
    $ dagger call pixi install-environments \
        --environments default \
        --environments docs \
        --environments model
    ```

=== "Python SDK"

    ```python
    ctr = await dag.pixi(source=src).install_environments(
        environments=["default", "docs", "model"],
    )
    ```

Use `install_all_environments` when the container should include every environment
declared by the workspace.

## Choose the entrypoint environment

A runtime image may carry several Pixi environments, but its entrypoint activates
one of them.

```python
runtime = await dag.pixi(source=src).runtime_environments(
    environments=["default", "docs", "model"],
    entrypoint_environment="model",
)
```

That image contains `.pixi/envs/default`, `.pixi/envs/docs`, and
`.pixi/envs/model`. The entrypoint activates `.pixi/envs/model`.

## Features are not installed directly

Do not pass feature names to the module unless an environment has the same name.
Pixi may define a feature called `docs`, but the install target is the environment
declared under `[tool.pixi.environments]` or `[environments]`.

```toml
[tool.pixi.feature.docs.dependencies]
mkdocs = ">=1.6,<2"

[tool.pixi.environments]
documentation = { features = ["docs"], no-default-feature = true }
```

Install `documentation`, not `docs`:

```console
$ dagger call pixi install --environment documentation
```

See Pixi's own documentation for the full environment and feature grammar:
[Pixi environments](https://pixi.prefix.dev/latest/workspace/environment/) and
[multi-environment workspaces](https://pixi.prefix.dev/latest/workspace/multi_environment/).

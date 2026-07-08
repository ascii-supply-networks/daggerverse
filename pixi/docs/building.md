---
icon: lucide/package
title: Building containers
description: Install Pixi environments in Dagger containers and build runtime images without shipping Pixi itself.
---

# Building containers

This is the module's core feature: turning a [Pixi](https://pixi.prefix.dev/latest/)
workspace into a [Dagger](https://dagger.io) container with one or more named
environments installed.

Pixi remains responsible for solving, locking, and installing. The module provides
the Dagger shape around it: source mounting, cache volumes, environment selection,
Dagger SDK codegen overlays, and runtime images that keep the installed
`.pixi/envs/*` directories but leave the Pixi binary behind.

??? abstract "The mental model"

    ```mermaid
    graph LR
      P["Pixi<br/><i>source tree</i>"] -->|workspace / get_workspaces| WS["PixiWorkspaceSource<br/><i>one per pixi.lock</i>"]
      P -->|install / run / runtime| Root["Default workspace<br/><i>path = .</i>"]
      WS -->|install_environments| Builder["Builder container<br/><i>Pixi image</i>"]
      Builder -->|runtime_environments| Runtime["Runtime container<br/><i>no Pixi binary</i>"]
    ```

    - **`Pixi`** holds your source tree. Its root functions use the workspace at `.`
      and accept `path` when your Pixi workspace lives deeper in the tree.
    - **`PixiWorkspaceSource`** is one Pixi workspace rooted at a `pixi.lock`. It is
      useful when you want to keep a workspace object around explicitly.
    - **Builder containers** use a Pixi image and can run `pixi install` / `pixi run`.
    - **Runtime containers** copy selected `.pixi/envs/*` directories and an
      entrypoint into a fresh image.

## `install` - the one-call path

`install` returns a builder-style container with one Pixi environment installed.

=== "CLI"

    ```console
    $ dagger call pixi install --environment default
    ```

=== "Python SDK"

    ```python
    from dagger import dag

    ctr = await dag.pixi(source=src).install(environment="default")
    ```

Use `run` for a one-off command in that environment:

=== "CLI"

    ```console
    $ dagger call pixi run --args python --args --version
    ```

=== "Python SDK"

    ```python
    ctr = await dag.pixi(source=src).run(args=["python", "--version"])
    ```

## Lockfile mode

Install, run, and runtime image methods default to Pixi's `--locked` mode for
compatibility. Use `lockfile_mode="frozen"` for CI/container builds that must
fail when `pixi.lock` is stale.

=== "CLI"

    ```console
    $ dagger call pixi install --environment default --lockfile-mode frozen
    ```

=== "Python SDK"

    ```python
    ctr = await dag.pixi(source=src).install(
        environment="default",
        lockfile_mode="frozen",
    )
    ```

## Multiple environments

`install_environments` installs several Pixi environments into the same builder
container.

=== "CLI"

    ```console
    $ dagger call pixi install-environments \
        --environments default \
        --environments docs
    ```

=== "Python SDK"

    ```python
    ctr = await dag.pixi(source=src).install_environments(
        environments=["default", "docs"],
    )
    ```

To install every declared environment, use `install_all_environments`.

## Runtime images

Use `runtime` or `runtime_environments` for deployable images. The module installs
with Pixi in a builder, copies the selected `.pixi/envs/*` directories and a Bash
entrypoint into a runtime image, and leaves the Pixi binary behind.

=== "CLI"

    ```console
    $ dagger call pixi runtime-environments \
        --environments default \
        --environments model-downloader \
        --entrypoint-environment default
    ```

=== "Python SDK"

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

`runtime_source_paths` is source-root-relative and accepts paths or glob patterns.
For a nested Pixi workspace, include the workspace prefix when needed.

## Choosing images

The default builder image is `ghcr.io/prefix-dev/pixi:0.70.2`, or the concrete
version resolved from `requires-pixi` when the workspace declares one. Pass
`pixi_version` or `image` to override it.

The default runtime image is `ubuntu:noble`. Pass `runtime_image` or
`runtime_base_container` when the final image needs operating-system packages,
users, certificates, or another base.

## Dagger modules as dependencies

If the workspace is itself a Dagger module, the module runs Dagger codegen and
overlays the generated SDK before installing, so the generated `dagger-io` package
is present even when `sdk/` is gitignored in CI. This is on by default and is a
no-op for non-Dagger projects.

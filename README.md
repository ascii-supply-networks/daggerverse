# ASCII Daggerverse

Shared [Dagger](https://dagger.io) modules.

Add as a dependency to another [Dagger](https://dagger.io) module:

```console
$ dagger install github.com/ascii-supply-networks/daggerverse/pixi
```

This project is heavily inspired by the
[`typesafe-ai/daggerverse`](https://github.com/typesafe-ai/daggerverse)
repository. Python package publishing should use `ascii-daggerverse` to avoid
colliding with the upstream project name.

## Modules

| Module | Description |
|--------|-------------|
| [`pixi`](./pixi) | Tooling for [Pixi](https://pixi.prefix.dev/latest/)-managed Python projects: verify checked-in `pixi.lock` files, install one or many environments in the same [Dagger](https://dagger.io) container, build filtered runtime images without Pixi, and run commands through Pixi. |

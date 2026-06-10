---
icon: lucide/lock
title: Lock checks
description: Verify committed Pixi locks from Dagger.
---

# Lock Checks

`pixi:locked` runs `pixi lock --check` through [Dagger](https://dagger.io) for
every discovered workspace.
This fails when a manifest and `pixi.lock` are out of sync.

```console
dagger check pixi:locked
```

Use `exclude` to skip fixtures or generated workspaces:

```console
dagger check pixi:locked --exclude "**/tests/_packages/**"
```

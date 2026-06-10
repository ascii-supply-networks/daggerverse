---
icon: simple/githubactions
title: GitHub Actions
description: Run Pixi and Dagger checks, publish the module, and deploy docs from GitHub Actions.
---

# GitHub Actions

Workflows:

- `CI.yml` runs Pixi tests, lint, formatting, hooks, and root Dagger checks.
- `security-audit.yml` audits PyPI packages recorded in `pixi.lock`.
- `upstream-watch.yml` watches `typesafe-ai/daggerverse` for relevant upstream changes.
- `publish.yml` publishes a [Daggerverse](https://daggerverse.dev) module when a module tag is pushed.
- `deploy-docs.yml` builds the Zensical docs with [Dagger](https://dagger.io) and deploys them to GitHub Pages.

## CI

```console
pixi run --frozen test
pixi run --frozen lint
pixi run --frozen format-check
pixi run --frozen dagger-check
pixi run --frozen pre-commit-run-all
```

`dagger-check` downloads the pinned Dagger CLI and runs `dagger check`.

CI also runs the Pixi test, lint, format, and audit tasks on Windows x64 and
Windows ARM64. Hooks run on Windows x64 only.

## Security Audit

`security-audit.yml` parses `pixi.lock` and runs `pip-audit` against PyPI
packages.

```console
pixi run --frozen audit-pypi
pixi run --frozen pin-actions
pixi run --frozen audit-github-actions
```

## Upstream Watch

`upstream-watch.yml` compares `typesafe-ai/daggerverse` against
`.github/upstream-watch.json` and updates one tracking issue.

```console
pixi run --frozen upstream-watch
```

After review, update `base_commit` to the latest reviewed upstream SHA.

## Publishing

Push a module tag to publish:

```console
git tag pixi/v0.1.0
git push origin pixi/v0.1.0
```

The publish workflow extracts `pixi` from the tag name and runs:

```console
pixi run --frozen python scripts/run_dagger.py publish -m ./pixi
```

## Required Repository Settings

- Add `DAGGER_CLOUD_TOKEN` to the `daggger-publish` environment.
- Enable GitHub Actions.
- Enable GitHub Pages when `deploy-docs.yml` should publish the generated site.

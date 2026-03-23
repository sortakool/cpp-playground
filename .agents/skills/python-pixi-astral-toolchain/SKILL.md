---
name: python-pixi-astral-toolchain
description: Repository-local hub for the Python, Pixi, and Astral toolchain in this repo. Use when working on Python files, `pyproject.toml`, `uv.lock`, `.python-version`, `pixi.toml`, `mise.toml`, `.devcontainer/devcontainer.json`, and minimal Python helper flows (`finalize-bootstrap`, `verify run`, devcontainer runtime helpers).
---

# Python Pixi Astral Toolchain

Use this skill as the routing and policy layer for Python-tooling work in this repository.

## Repository Policy

- Treat `uv`, `ruff`, and `ty` as one coordinated quality toolchain.
- Treat `pixi` as the locked environment and task layer.
- Treat `mise` as the exact fast-moving CLI pin layer.
- Prefer declarative checked-in configuration over ad-hoc command-line flags.
- Keep linting, formatting, typing, dead code detection, duplication checks, modernization, and related static analysis enabled by default.
- If Ruff does not cover a category well enough, add one focused supplemental tool with declarative config instead of ad-hoc commands.

## Load Order

1. Load the canonical combined policy skill:

- `/Users/rmanaloto/.codex/skills/python-pixi-astral-toolchain/SKILL.md`

2. Then load the specialized skill that matches the task:

- Repo Pixi and devcontainer workflow:
  `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills/pixi-devcontainer/SKILL.md`
- Ruff workflow:
  `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills/ruff/SKILL.md`
- Ty workflow:
  `/Users/rmanaloto/.codex/skills/astral-ty/SKILL.md`
- uv workflow:
  `/Users/rmanaloto/.codex/skills/uv-package-manager/SKILL.md`

## Routing Rules

### Load `pixi-devcontainer`

Load it when the task touches:

- `pixi.toml`
- `pixi.lock`
- `mise.toml`
- `.devcontainer/devcontainer.json`
- root `Dockerfile` or `docker-bake.hcl` build-interface coordination
- bootstrap, refresh, validate, or prove flows
- devcontainer PATH, mounts, image bootstrap, or environment tasks
- host-side `chezmoi` / `mise` / `pixi` interaction for this repo

### Load `ruff`

Load it when the task touches:

- `ruff` linting or formatting
- Ruff config in `pyproject.toml`, `ruff.toml`, or `.ruff.toml`
- Ruff-driven modernization, security linting, dead-code cleanup, or complexity cleanup

### Load `astral-ty`

Load it when the task touches:

- `ty` config or type-checking behavior
- `ty check`
- type suppressions, type fixes, or Ty editor integration

### Load `uv-package-manager`

Load it when the task touches:

- `uv.lock`
- `.python-version`
- dependency changes
- `uv add`, `uv sync`, `uv lock`, `uv run`, or `uv tool install`

## Verification Defaults

Prefer the repo-defined commands first:

```bash
uv run finalize-bootstrap
uv run verify run
pixi run ruff-check
pixi run ty-check
```

For kernel-sensitive work, follow `docs/latest-kernel-testing.md` instead of assuming the devcontainer owns the kernel.

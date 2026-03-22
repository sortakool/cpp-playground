---
name: pixi-devcontainer
description: Repository-specific Pixi, mise, uv, and devcontainer workflow for this repo. Use when editing `pixi.toml`, `pixi.lock`, `mise.toml`, `.devcontainer/devcontainer.json`, `tooling/control_plane.py`, bootstrap or prove flows, devcontainer PATH or mounts, or host-side chezmoi/mise/pixi/uv integration for the development environment.
---

# Pixi Devcontainer

Use this skill for the concrete environment-management workflow in this repository.

## Source Of Truth

- `mise.toml`: exact pins for fast-moving CLIs such as `uv`, `pixi`, `chezmoi`, `codex`, `claude-code`, and `gemini-cli`
- `pixi.toml`: locked helper environments, Python helper dependencies, Ruff, Ty, and named tasks
- `.devcontainer/devcontainer.json`: devcontainer runtime wiring, mounts, PATH layering, and `postCreateCommand`
- `tooling/control_plane.py`: bootstrap, lock refresh, validation, and prove orchestration
- `.devcontainer/Dockerfile`: compiler, sanitizer, profiler, and debugger image changes

Do not collapse these layers into one tool.

## Pixi Rules

- Prefer `pixi install --locked` when `pixi.lock` exists.
- Commit and maintain `pixi.lock`; treat it as part of the reproducible environment contract.
- Prefer `pixi run <task>` for repo-defined tasks instead of recreating long commands manually.
- Keep Ruff and Ty task entry points in `pixi.toml` when the repo already exposes them there.
- Treat Pixi environments such as `llvm-stable` and `gcc-stable` as the mechanism for stable toolchain lanes.
- Use `pixi run -e <env> ...` when the build or test flow needs a specific named environment.
- Use `pixi exec ...` only for true one-off commands that are not already modeled as tasks.
- Avoid `pixi shell` in automation or instructions unless the task is explicitly interactive.
- Do not introduce `pixi init`, `pixi global`, or ad-hoc feature layouts unless the user is explicitly changing the repository's environment model.

## uv Rules

- Use `uv` under the covers for Python tool execution and tool installs that the control plane already manages.
- Prefer `uv run ...` for project Python commands when the task belongs to the Python control plane.
- Prefer `uv tool install --python <version> --upgrade <tool>` only when matching the existing bootstrap pattern.
- Do not replace Pixi environment tasks with standalone `uv` flows when the repo already models that step in `pixi.toml`.

## mise and chezmoi Rules

- Treat `mise` as the checked-in exact CLI pin layer, not as a fallback for task execution.
- Prefer `mise trust .`, `mise install --locked`, and `mise reshim` through the existing control-plane flow instead of inventing new setup commands.
- Treat `chezmoi` as a host-side dotfile/config delivery mechanism, not as a replacement for repo-owned manifests.
- If host environment variables or secrets are needed, prefer the existing host-side secret workflow and devcontainer env wiring over hardcoding values into repo config.

## Devcontainer Workflow

For the daily Linux `amd64` environment, use this sequence:

1. Build or refresh the wrapper image:

```bash
python3 -m tooling build-devcontainer-image
```

2. Open the repo in the devcontainer.

3. Bootstrap the locked user-space tools:

```bash
python3 -m tooling bootstrap
```

This currently performs:

- `pixi install --locked` when `pixi.lock` exists
- `mise trust <repo>`
- `mise install --locked`
- `mise reshim`
- `uv tool install` for repo-managed helper tools such as `gcovr` and `cmakelang`

4. Validate and prove the devcontainer surface:

```bash
python3 -m tooling validate --mode all
pixi run prove-devcontainer
```

Prefer the repo tasks in `pixi.toml` over hand-written command sequences whenever an equivalent task already exists.

## Verification

Prefer the repo-defined commands in this order:

```bash
python3 -m tooling validate --mode repo
python3 -m tooling validate --mode runtime
pixi run ruff-check
pixi run ty-check
pixi run prove-devcontainer
```

If changing environment manifests or tool pins, also verify the lockfiles and refresh flow:

```bash
python3 -m tooling refresh
python3 -m tooling validate --mode all
```

For kernel-sensitive flows, follow `docs/latest-kernel-testing.md` instead of assuming the devcontainer owns the kernel.

## Related Files

- `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/pyproject.toml`
- `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/pixi.toml`
- `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/mise.toml`
- `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.devcontainer/devcontainer.json`
- `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/tooling/control_plane.py`
- `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/README.md`
- `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/CLAUDE.md`

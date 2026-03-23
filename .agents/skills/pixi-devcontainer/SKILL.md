---
name: pixi-devcontainer
description: Repository-specific Pixi, mise, uv, and devcontainer workflow for this repo. Use when editing `pixi.toml`, `pixi.lock`, `mise.toml`, `.devcontainer/devcontainer.json`, or bootstrap/verify flows tied to the minimal Python helper surface.
---

# Pixi Devcontainer

Use this skill for the concrete environment-management workflow in this repository.

## Source Of Truth

- `mise.toml`: exact pins for fast-moving CLIs such as `uv`, `pixi`, `chezmoi`, `codex`, `claude-code`, and `gemini-cli`
- `pixi.toml`: locked helper environments and leaf checks
- `.devcontainer/devcontainer.json`: devcontainer runtime wiring, mounts, PATH layering, and `postCreateCommand`
- `Dockerfile` (root): `base`, `clang`, `gcc`, `final`, `devcontainer` stage topology
- `docker-bake.hcl`: image build interface

Do not collapse these layers into one tool.

## Pixi Rules

- Prefer `pixi install --locked` when `pixi.lock` exists.
- Commit and maintain `pixi.lock`; treat it as part of the reproducible environment contract.
- Keep Pixi focused on locked environments and leaf verification checks.
- Use `pixi run -e <env> ...` only when a named environment is explicitly required.
- Use `pixi exec ...` only for true one-off commands.
- Avoid `pixi shell` in automation or instructions unless the task is explicitly interactive.
- Do not introduce `pixi init`, `pixi global`, or ad-hoc feature layouts unless the user is explicitly changing the repository's environment model.

## uv Rules

- Use `uv` under the covers for Python tool execution and installs the repo pins.
- Prefer explicit module entrypoints for repo helpers:
  - `finalize-bootstrap`
  - `verify run`

## mise and chezmoi Rules

- Treat `mise` as the checked-in exact CLI pin layer, not as a fallback for task execution.
- Treat `chezmoi` as a host-side dotfile/config delivery mechanism, not as a replacement for repo-owned manifests.
- Treat `home/` dotfiles as `chezmoi` managed with `dot_` naming.
- If host environment variables or secrets are needed, prefer the existing host-side secret workflow and devcontainer env wiring over hardcoding values into repo config.

## Devcontainer Workflow

For the daily Linux `amd64` environment, use this sequence:

1. Build or refresh the image graph:

```bash
docker buildx bake -f docker-bake.hcl devcontainer --load
```

2. Open the repo in the devcontainer.

3. Bootstrap the locked user-space tools:

```bash
./install.sh
uv run finalize-bootstrap
```

4. Validate and prove the devcontainer surface:

```bash
uv run verify run
```

Prefer the repo tasks in `pixi.toml` over hand-written command sequences whenever an equivalent task already exists.

For runtime user/SSH helper flows, prefer the checked-in devcontainer runtime helper modules instead of shell scripts.
On macOS with Docker Desktop, keep the checked-in SSH proxy chain:
- host launchd SSH socket -> host-local TCP proxy recorded under `~/.local/state/cpp-playground/`
- container-local UNIX socket at `/tmp/cpp-playground-ssh-agent.sock`

Do not replace that flow with a host `~/.ssh` bind mount or a direct bind-mounted host UNIX socket.

## Verification

Prefer the repo-defined commands in this order:

```bash
uv run verify run
pixi run ruff-check
pixi run ty-check
```

For kernel-sensitive flows, follow `docs/latest-kernel-testing.md` instead of assuming the devcontainer owns the kernel.
For SSH-specific validation after runtime changes, also use:

```bash
python3 -m cpp_playground.devcontainer_runtime smoke-ssh
```

Treat `gh auth status` inside the container as best-effort only. SSH parity is proven by matching agent identities plus successful SSH-backed Git operations.

## Related Files

- `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/pyproject.toml`
- `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/pixi.toml`
- `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/mise.toml`
- `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.devcontainer/devcontainer.json`
- `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/Dockerfile`
- `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/docker-bake.hcl`
- `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/README.md`
- `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/CLAUDE.md`
